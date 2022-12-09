import argparse
import dataclasses
import json
import logging
import os
import re
import sys
from typing import List

import parsel
import requests


logging.basicConfig(format='[%(process)d]:%(levelname)s:%(funcName)s:%(lineno)d: %(message)s', level=logging.INFO)
LOGGER = logging.getLogger()


@dataclasses.dataclass
class VideoFile:
    file_path: str
    scrubbed_file_name: str = ''
    year: int = 0
    imdb_tt: str = ''


def get_imdb_search_results(video_file: VideoFile) -> str:
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:107.0) Gecko/20100101 Firefox/107.0',
        'Referer': 'https://www.imdb.com/'
    }
    name = video_file.scrubbed_file_name.strip()
    name = re.sub(r' +', '+', name)
    url = f'https://www.imdb.com/find?q={name}'
    if video_file.year:
        url += f'+{video_file.year}'

    imdb_response = requests.get(url, headers=headers)
    imdb_response_text = imdb_response.text

    # For testing, save a copy of the file
    with open('/tmp/imdb_search_response.txt', 'w', encoding='utf8') as f:
        f.write(imdb_response_text)

    return imdb_response_text


def get_imdb_tt_info(video_file: VideoFile) -> str:
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:107.0) Gecko/20100101 Firefox/107.0',
        'Referer': 'https://www.imdb.com/'
    }
    imdb_tt = video_file.imdb_tt
    url = f'https://www.imdb.com/title/{imdb_tt}/'

    imdb_response = requests.get(url, headers=headers)
    imdb_response_text = imdb_response.text

    # For testing, save a copy of the file
    with open('/tmp/imdb_tt_response.txt', 'w', encoding='utf8') as f:
        f.write(imdb_response_text)

    return imdb_response_text


def parse_imdb_search_results(imdb_response_text: str, video_file: VideoFile):
    imdb_response_selector = parsel.Selector(text=imdb_response_text)
    search_result_selectors = imdb_response_selector.xpath("//section[@data-testid='find-results-section-title']/div/ul/li")
    for search_result_selector in search_result_selectors:
        # title_selector = search_result_selector.xpath(".//div/div/a")
        # title_text = title_selector.xpath("text()").get()
        # imdb_tt_url = title_selector.attrib['href']
        # match = re.match(r'/title/(tt\d+).*', imdb_tt_url)
        # imdb_tt = match.group(1)

        title_text = search_result_selector.xpath(".//div/div/a/text()").get()
        imdb_tt_url = search_result_selector.xpath(".//div/div/a/@href").get()
        match = re.match(r'/title/(tt\d+).*', imdb_tt_url)
        imdb_tt = match.group(1)

        year_selector, actors_selector = search_result_selector.xpath(".//div/div/ul")
        year = year_selector.xpath(".//li/label/text()").get()
        actors = actors_selector.xpath(".//li/label/text()").get()
        LOGGER.info('Found: title="%s", year="%s", actors="%s", imdb_tt="%s"', title_text, year, actors, imdb_tt)


def parse_imdb_tt_results(imdb_response_text: str, video_file: VideoFile):
    imdb_response_selector = parsel.Selector(text=imdb_response_text)
    # search_result_selectors = imdb_response_selector.xpath("//section[@data-testid='find-results-section-title']/div/ul/li")
    # for search_result_selector in search_result_selectors:
    #     # title_selector = search_result_selector.xpath(".//div/div/a")
    #     # title_text = title_selector.xpath("text()").get()
    #     # imdb_tt_url = title_selector.attrib['href']
    #     # match = re.match(r'/title/(tt\d+).*', imdb_tt_url)
    #     # imdb_tt = match.group(1)
    #
    #     title_text = search_result_selector.xpath(".//div/div/a/text()").get()
    #     imdb_tt_url = search_result_selector.xpath(".//div/div/a/@href").get()
    #     match = re.match(r'/title/(tt\d+).*', imdb_tt_url)
    #     imdb_tt = match.group(1)
    #
    #     year_selector, actors_selector = search_result_selector.xpath(".//div/div/ul")
    #     year = year_selector.xpath(".//li/label/text()").get()
    #     actors = actors_selector.xpath(".//li/label/text()").get()
    #     LOGGER.info('Found: title="%s", year="%s", actors="%s", imdb_tt="%s"', title_text, year, actors, imdb_tt)


def scrub_video_file_name(file_name: str, filename_metadata_tokens: str) -> (str, int):
    year = 0

    match = re.match(r'((.*)\((\d{4})\))', file_name)
    if match:
        file_name = match.group(2)
        year = int(match.group(3))
        scrubbed_file_name_list = file_name.replace('.', ' ').split()

    else:
        metadata_token_list = [token.lower().strip() for token in filename_metadata_tokens.split(',')]
        file_name_parts = file_name.replace('.', ' ').split()
        scrubbed_file_name_list = list()

        for file_name_part in file_name_parts:
            file_name_part = file_name_part.lower()

            if file_name_part in metadata_token_list:
                break
            scrubbed_file_name_list.append(file_name_part)

        if scrubbed_file_name_list:
            match = re.match(r'\(?(\d{4})\)?', scrubbed_file_name_list[-1])
            if match:
                year = int(match.group(1))
                del scrubbed_file_name_list[-1]

    scrubbed_file_name = ' '.join(scrubbed_file_name_list).strip()
    scrubbed_file_name = re.sub(' +', ' ', scrubbed_file_name)
    return scrubbed_file_name, year


def scan_folder(folder_path: str, ignore_extensions: str, filename_metadata_tokens: str) -> List[VideoFile]:
    ignore_extensions_list = [ext.lower().strip() for ext in ignore_extensions.split(',')]

    video_files = list()

    for dir_path, dirs, files in os.walk(folder_path):
        for filename in files:
            file_path = os.path.join(dir_path, filename)
            filename_parts = os.path.splitext(filename)
            filename_no_extension = filename_parts[0]
            filename_extension = filename_parts[1]
            if filename_extension.startswith('.'):
                filename_extension = filename_extension[1:]

            if filename_extension.lower() in ignore_extensions_list:
                continue

            scrubbed_video_file_name, year = scrub_video_file_name(filename_no_extension, filename_metadata_tokens)
            video_file = VideoFile(file_path=file_path, scrubbed_file_name=scrubbed_video_file_name, year=year)
            video_files.append(video_file)

    return video_files


def main(argv):
    video_file = VideoFile(file_path='', scrubbed_file_name='kiss kiss bang bang', year=2005, imdb_tt='tt0373469')
    # get_imdb_search_results(video_file)
    get_imdb_tt_info(video_file)

    with open('/tmp/imdb_search_response.txt') as f:
        imdb_text = f.read()
    parse_imdb_search_results(imdb_text, video_file)

    with open('/tmp/imdb_tt_response.txt') as f:
        imdb_text = f.read()
    parse_imdb_tt_results(imdb_text, video_file)

    parser = argparse.ArgumentParser()
    parser.add_argument('--folder', action='store', help='Path to folder to process')
    parser.add_argument('--ignore-extensions', action='store', default='png,jpg,nfo', help='File extensions to ignore (comma-separated list)')
    parser.add_argument('--filename-metadata-tokens', action='store', default='480p,720p,1080p,bluray,hevc,x265,x264,web,webrip,web-dl,repack,proper,extended,remastered,dvdrip,dvd,hdtv,xvid,hdrip,brrip,dvdscr,pdtv', help='Filename metadata elements')
    parser.add_argument('--save-file', action='store', default='video_info.json', help='Name of file used to save JSON data')
    args = parser.parse_args(argv)

    if args.folder:
        LOGGER.info('Scanning folder %s', args.folder)
        video_files = scan_folder(args.folder, args.ignore_extensions, args.filename_metadata_tokens)

        max_len = -1
        for video_file in video_files:
            len_scrubbed_file_name = len(video_file.scrubbed_file_name)
            max_len = max(max_len, len_scrubbed_file_name)

        for video_file in video_files:
            file_path = video_file.file_path
            file_name_with_ext = os.path.basename(file_path)
            filename_parts = os.path.splitext(file_name_with_ext)
            file_name = filename_parts[0]

            if video_file.year:
                LOGGER.info(f'{video_file.scrubbed_file_name:{max_len}} ({video_file.year}) <-- {file_name} [{file_path}]')
            else:
                LOGGER.info(f'{video_file.scrubbed_file_name:{max_len}} ({video_file.year}) <-- {file_name} [{file_path}]')

        LOGGER.info('Saving results %s', args.save_file)
        with open(args.save_file, 'w') as f:
            json_list = [dataclasses.asdict(video_file) for video_file in video_files]
            json_str = json.dumps(json_list, indent=4)
            f.write(json_str)


if __name__ == '__main__':
    main(sys.argv[1:])
