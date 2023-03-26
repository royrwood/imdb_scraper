import dataclasses
import os
import re
from typing import List

import parsel
import requests


@dataclasses.dataclass
class VideoFile:
    file_path: str = ''
    scrubbed_file_name: str = ''
    scrubbed_file_year: str = ''
    imdb_tt: str = ''
    imdb_name: str = ''
    imdb_year: str = ''
    imdb_rating: str = ''
    imdb_genres: List[str] = None
    imdb_plot: str = None
    is_dirty: bool = False


@dataclasses.dataclass
class IMDBInfo:
    imdb_tt: str = ''
    imdb_name: str = ''
    imdb_year: str = ''
    imdb_rating: str = ''
    imdb_genres: List[str] = None
    imdb_plot: str = ''
    details_fully_loaded: bool = False


def get_parse_imdb_search_results(video_name: str, year: str = None) -> List[IMDBInfo]:
    imdb_response_text = get_imdb_search_results(video_name, year)

    return parse_imdb_search_results(imdb_response_text)


def get_imdb_search_results(video_name: str, year: str = None) -> str:
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:107.0) Gecko/20100101 Firefox/107.0',
        'Referer': 'https://www.imdb.com/'
    }
    name = video_name.strip()
    name = re.sub(r' +', '+', name)
    url = f'https://www.imdb.com/find?q={name}'
    if year:
        url += f'+{year}'

    imdb_response = requests.get(url, headers=headers, timeout=(5.0, 25.0))

    if imdb_response.status_code != 200:
        raise Exception(f'HTTP {imdb_response.status_code} while fetching search results for {video_name}')

    imdb_response_text = imdb_response.text

    # For testing, save a copy of the file
    with open('/tmp/imdb_search_response.txt', 'w', encoding='utf8') as f:
        f.write(imdb_response_text)

    return imdb_response_text


def get_parse_imdb_tt_info(imdb_tt: str) -> IMDBInfo:
    imdb_response_text = get_imdb_tt_info(imdb_tt)

    return parse_imdb_tt_results(imdb_response_text, imdb_tt)


def get_imdb_tt_info(imdb_tt: str) -> str:
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:107.0) Gecko/20100101 Firefox/107.0',
        'Referer': 'https://www.imdb.com/'
    }
    imdb_tt = imdb_tt
    url = f'https://www.imdb.com/title/{imdb_tt}/'

    imdb_response = requests.get(url, headers=headers, timeout=(5.0, 25.0))
    imdb_response_text = imdb_response.text

    # For testing, save a copy of the file
    with open('/tmp/imdb_tt_response.txt', 'w', encoding='utf8') as f:
        f.write(imdb_response_text)

    return imdb_response_text


def parse_imdb_search_results(imdb_response_text: str) -> List[IMDBInfo]:
    match_video_files = list()
    imdb_response_selector = parsel.Selector(text=imdb_response_text)
    search_result_selectors = imdb_response_selector.xpath("//section[@data-testid='find-results-section-title']/div/ul/li")
    for search_result_selector in search_result_selectors:
        imdb_title = search_result_selector.xpath(".//div/div/a/text()").get() or ''
        imdb_year = search_result_selector.xpath(".//div/div/ul[1]/li/label/text()").get() or ''
        imdb_tt_url = search_result_selector.xpath(".//div/div/a/@href").get() or ''
        imdb_tt = re.match(r'/title/(tt\d+).*', imdb_tt_url).group(1) or ''

        imdb_year = imdb_year[:4]
        if not imdb_year.isdigit():
            imdb_year = ''

        match_video_file = IMDBInfo(imdb_tt=imdb_tt, imdb_name=imdb_title, imdb_year=imdb_year)
        match_video_files.append(match_video_file)

    return match_video_files


def parse_imdb_tt_results(imdb_response_text: str, imdb_tt: str) -> IMDBInfo:
    imdb_response_selector = parsel.Selector(text=imdb_response_text)
    imdb_name = imdb_response_selector.xpath("//h1[@data-testid='hero-title-block__title']/text()").get()
    if not imdb_name:
        imdb_name = imdb_response_selector.xpath("//h1[@data-testid='hero__pageTitle']/span/text()").get()
    if not imdb_name:
        imdb_name = ''
    imdb_rating = imdb_response_selector.xpath("//div[@data-testid='hero-rating-bar__aggregate-rating__score']/span/text()").get() or ''
    imdb_genres = imdb_response_selector.xpath("//div[@data-testid='genres']/div/a/span/text()").getall()
    imdb_plot = imdb_response_selector.xpath("//span[@data-testid='plot-xl']/text()").get() or ''
    imdb_year = imdb_response_selector.xpath("/html/body/div[2]/main/div/section[1]/section/div[3]/section/section/div[2]/div[1]//li/a/text()").get()
    if not imdb_year:
        imdb_year = imdb_response_selector.xpath("/html/body/div[2]/main/div/section[1]/section/div[3]/section/section/div[2]/div[1]/div/ul/li//a/text()").get()
    if not imdb_year:
        imdb_year = imdb_response_selector.xpath("/html/body/div[2]/main/div/section[1]/section/div[3]/section/section/div[2]/div[1]/ul/li[1]/a/text()").get()
    if not imdb_year:
        imdb_year = ''
    if not re.search(r'\d\.\d', imdb_rating):
        imdb_rating = ''

    imdb_year = imdb_year[:4]
    if not imdb_year.isdigit():
        imdb_year = ''

    # foo = imdb_response_selector.xpath("/html/body/div[2]/main/div/section[1]/section/div[3]/section/section/div[2]/div[1]/div/ul/li[1]/a/text()").get()
    # foo = imdb_response_selector.xpath("/html/body/div[2]/main/div/section[1]/section/div[3]/section/section/div[2]/div[1]/div/ul/li[2]/a/text()").get()

    return IMDBInfo(imdb_tt=imdb_tt, imdb_rating=imdb_rating, imdb_genres=imdb_genres, imdb_name=imdb_name, imdb_plot=imdb_plot, imdb_year=imdb_year, details_fully_loaded=True)


def scrub_video_file_name(file_name: str, filename_metadata_tokens: str) -> (str, str):
    year = ''

    match = re.match(r'((.*)\((\d{4})\))', file_name)
    if match:
        file_name = match.group(2)
        year = match.group(3)
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
                year = match.group(1)
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
            video_file = VideoFile(file_path=file_path, scrubbed_file_name=scrubbed_video_file_name, scrubbed_file_year=year)
            video_files.append(video_file)

    return video_files
