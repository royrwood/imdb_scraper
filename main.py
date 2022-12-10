#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import dataclasses
import logging
import os
import json
import math
from typing import List, Optional

import imdb_scraper.imdb_utils
from imdb_scraper import curses_gui
from imdb_scraper import imdb_utils


class MyMenu(curses_gui.MainMenu):
    def __init__(self):
        super(MyMenu, self).__init__()
        self.video_files: Optional[List[imdb_scraper.imdb_utils.VideoFile]] = None
        self.video_files_is_dirty: bool = False

    def set_menu_choices(self):
        self.menu_choices = []
        self.menu_choices.append(('Scan Video Folder', self.scan_video_folder))
        self.menu_choices.append(('Load Video Info', self.load_video_file_data))

    def quit_confirm(self):
        if self.video_files_is_dirty:
            return False
        else:
            return True

    def display_video_file_data(self):
        max_len = -1
        for video_file in self.video_files:
            len_scrubbed_file_name = len(video_file.scrubbed_file_name)
            max_len = max(max_len, len_scrubbed_file_name)

        num_video_files = len(self.video_files)
        num_digits = math.floor(math.log10(num_video_files)) + 1

        video_info_lines = list()
        for i, video_file in enumerate(self.video_files):
            file_path = video_file.file_path
            file_name_with_ext = os.path.basename(file_path)
            filename_parts = os.path.splitext(file_name_with_ext)
            file_name = filename_parts[0]

            info = f'{i:0{num_digits}d} {video_file.scrubbed_file_name:{max_len}} ({video_file.year}) <-- {file_name} [{file_path}]'
            video_info_lines.append(info)

        with curses_gui.ScrollingPanel(rows=video_info_lines) as scrolling_panel:
            scrolling_panel.run()

    def save_video_file_data(self):
        final_message = 'Video data not saved'

        with curses_gui.InputPanel(prompt='Enter path to video file data: ', default_value='imdb_video_info.json') as input_panel:
            video_file_path = input_panel.run()
        input_panel.hide()

        if video_file_path:
            with open(video_file_path, 'w') as f:
                json_list = [dataclasses.asdict(video_file) for video_file in self.video_files]
                json_str = json.dumps(json_list, indent=4)
                f.write(json_str)
            final_message = f'Video saved to {video_file_path}'
            self.video_files_is_dirty = False

        with curses_gui.MessagePanel([final_message]) as message_panel:
            message_panel.run()

    def load_video_file_data(self):
        with curses_gui.InputPanel(prompt='Enter path to video file data: ', default_value='imdb_video_info.json') as input_panel:
            video_file_path = input_panel.run()
        if video_file_path is None:
            return

        with open(video_file_path, encoding='utf8') as f:
            video_files_json = json.load(f)

        self.video_files_is_dirty = False

        self.video_files = list()
        for video_file_dict in video_files_json:
            video_file = imdb_utils.VideoFile(**video_file_dict)
            self.video_files.append(video_file)

        self.display_video_file_data()

    def scan_video_folder(self):
        with curses_gui.InputPanel(prompt='Enter path to folder: ', default_value='/media/rrwood/Seagate Expansion Drive/Videos/') as input_panel:
            video_folder_path = input_panel.run()
        if video_folder_path is None:
            return

        ignore_extensions = 'png,jpg,nfo'
        filename_metadata_tokens = '480p,720p,1080p,bluray,hevc,x265,x264,web,webrip,web-dl,repack,proper,extended,remastered,dvdrip,dvd,hdtv,xvid,hdrip,brrip,dvdscr,pdtv'

        self.video_files = imdb_utils.scan_folder(video_folder_path, ignore_extensions, filename_metadata_tokens)
        self.video_files_is_dirty = True

        with curses_gui.ScrollingPanel(rows=['Save video info', 'Do not save video info']) as scrolling_panel:
            if scrolling_panel.pick_a_line_or_cancel() == 0:
                scrolling_panel.hide()
                self.save_video_file_data()

        self.display_video_file_data()


if __name__ == '__main__':
    logging.basicConfig(filename='/tmp/imdb_scraper.log', format='[%(process)d]:%(levelname)s:%(funcName)s:%(lineno)d: %(message)s', level=logging.INFO)

    logging.info('Starting up...')
    curses_gui.console_gui_main(MyMenu)
    logging.info('Ending.')
