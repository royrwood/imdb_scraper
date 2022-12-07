import argparse
from dataclasses import dataclass
import logging
import os
import re
import sys
from typing import List


logging.basicConfig(format='[%(process)d]:%(levelname)s:%(funcName)s:%(lineno)d: %(message)s', level=logging.INFO)
LOGGER = logging.getLogger()


VIDEOFILE_JSON_FILENAME = 'video_info.json'


@dataclass
class VideoFile:
    file_path: str
    scrubbed_file_name: str = ''
    imdb_ref_num: str = ''


def scrub_video_file_name(file_name: str, filename_metadata_tokens: str) -> str:
    match = re.match(r'(.*\((\d{4})\))', file_name)
    if match:
        file_name = match.group(1)
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
                scrubbed_file_name_list[-1] = f'({year})'

    scrubbed_file_name = ' '.join(scrubbed_file_name_list).strip()

    return scrubbed_file_name


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

            scrubbed_video_file_name = scrub_video_file_name(filename_no_extension, filename_metadata_tokens)
            video_file = VideoFile(file_path=file_path, scrubbed_file_name=scrubbed_video_file_name)
            video_files.append(video_file)

    return video_files


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('--folder', action='store', help='Path to folder to process')
    parser.add_argument('--ignore-extensions', action='store', default='png,jpg,nfo', help='File extensions to ignore (comma-separated list)')
    parser.add_argument('--filename-metadata-tokens', action='store', default='480p,720p,1080p,bluray,hevc,x265,x264,web,webrip,web-dl,repack,proper,extended,remastered,dvdrip,dvd,hdtv,xvid,hdrip,brrip,dvdscr,pdtv', help='Filename metadata elements')
    args = parser.parse_args(argv)

    if args.folder:
        video_files = scan_folder(args.folder, args.ignore_extensions, args.filename_metadata_tokens)

        for video_file in video_files:
            file_path = video_file.file_path
            file_name_with_ext = os.path.basename(file_path)
            filename_parts = os.path.splitext(file_name_with_ext)
            file_name = filename_parts[0]

            match = re.match(r'.*\(?(\d{4})\)?', video_file.scrubbed_file_name)
            if not match:
                LOGGER.info(f'{video_file.scrubbed_file_name} <-- {file_name} [{file_path}]')


if __name__ == '__main__':
    main(sys.argv[1:])
