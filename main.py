import sys
import os
import re
import argparse
from dataclasses import dataclass
from typing import List


VIDEOFILE_JSON_FILENAME = 'video_info.json'


@dataclass
class VideoFile:
    file_path: str
    scrubbed_file_name: str = ''
    imdb_ref_num: str = ''


def scrub_video_file_name(file_name: str, filename_metadata_tokens: str) -> str:
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

    for dir_entry in os.scandir(folder_path):  # type: os.DirEntry
        if dir_entry.is_file():
            filename_parts = os.path.splitext(dir_entry.name)
            file_name = filename_parts[0]
            file_extension = filename_parts[1]
            if file_extension.startswith('.'):
                file_extension = file_extension[1:]

            if file_extension.lower() in ignore_extensions_list:
                # print(f'IGNORING: {dir_entry.name}')
                continue

            scrubbed_video_file_name = scrub_video_file_name(file_name, filename_metadata_tokens)
            video_file = VideoFile(file_path=dir_entry.path, scrubbed_file_name=scrubbed_video_file_name)
            video_files.append(video_file)

    return video_files


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('--folder', action='store', help='Path to folder to process')
    parser.add_argument('--ignore-extensions', action='store', default='png,jpg,nfo', help='File extensions to ignore (comma-separated list)')
    parser.add_argument('--filename-metadata-tokens', action='store', default='480p,720p,bluray,hevc,x265,x264,web,webrip,web-dl,repack,proper', help='Filename metadata elements')
    args = parser.parse_args(argv)

    if args.folder:
        video_files = scan_folder(args.folder, args.ignore_extensions, args.filename_metadata_tokens)

        for video_file in video_files:
            file_name_with_ext = os.path.basename(video_file.file_path)
            filename_parts = os.path.splitext(file_name_with_ext)
            file_name = filename_parts[0]
            print(f'{file_name} -> {video_file.scrubbed_file_name}')


if __name__ == '__main__':
    main(sys.argv[1:])
