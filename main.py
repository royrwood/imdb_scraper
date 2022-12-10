#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import math

from imdb_scraper import curses_gui
from imdb_scraper import imdb_utils


class MyMenu(curses_gui.MainMenu):
    def __init__(self):
        super(MyMenu, self).__init__()

    def set_menu_choices(self):
        self.menu_choices = []
        self.menu_choices.append(('Some menu choice', self.class_callback_function))
        self.menu_choices.append(('Scan Video Folder', scan_video_folder))

    def class_callback_function(self):
        logging.info('Callback for some menu choice (class method callback)')


def scan_video_folder():
    with curses_gui.InputPanel(prompt='Enter path to folder: ', default_value='/media/rrwood/Seagate Expansion Drive/Videos/') as input_panel:
        video_folder_path = input_panel.run()
    if video_folder_path is None:
        return

    ignore_extensions = 'png,jpg,nfo'
    filename_metadata_tokens = '480p,720p,1080p,bluray,hevc,x265,x264,web,webrip,web-dl,repack,proper,extended,remastered,dvdrip,dvd,hdtv,xvid,hdrip,brrip,dvdscr,pdtv'

    video_files = imdb_utils.scan_folder(video_folder_path, ignore_extensions, filename_metadata_tokens)

    max_len = -1
    for video_file in video_files:
        len_scrubbed_file_name = len(video_file.scrubbed_file_name)
        max_len = max(max_len, len_scrubbed_file_name)

    num_video_files = len(video_files)
    num_digits = math.floor(math.log10(num_video_files)) + 1
    logging.info(f'num_video_files={num_video_files}')
    logging.info(f'num_digits={num_digits}')

    video_info_lines = list()
    for i, video_file in enumerate(video_files):
        file_path = video_file.file_path
        file_name_with_ext = os.path.basename(file_path)
        filename_parts = os.path.splitext(file_name_with_ext)
        file_name = filename_parts[0]

        info = f'{i:0{num_digits}d} {video_file.scrubbed_file_name:{max_len}} ({video_file.year}) <-- {file_name} [{file_path}]'
        video_info_lines.append(info)

    with curses_gui.ScrollingPanel(rows=video_info_lines) as scrolling_panel:
        scrolling_panel.run()


if __name__ == '__main__':
    logging.basicConfig(filename='/tmp/imdb_scraper.log', format='[%(process)d]:%(levelname)s:%(funcName)s:%(lineno)d: %(message)s', level=logging.INFO)

    logging.info('Starting up...')
    curses_gui.console_gui_main(MyMenu)
    logging.info('Ending.')
