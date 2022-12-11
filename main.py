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
        self.video_file_path: str = 'imdb_video_info.json'
        self.video_files: Optional[List[imdb_scraper.imdb_utils.VideoFile]] = None
        self.video_files_is_dirty: bool = False
        self.logger = logging.getLogger()

    def set_menu_choices(self):
        self.menu_choices = []
        self.menu_choices.append(('Load Video Info', self.load_video_file_data))
        self.menu_choices.append(('Save Video Info', self.save_video_file_data))
        self.menu_choices.append(('Display Video Info', self.display_all_video_file_data))
        self.menu_choices.append(('Scan Video Folder', self.scan_video_folder))
        self.menu_choices.append((curses_gui.HorizontalLine(), None))
        self.menu_choices.append(('TEST COLUMN MODE', self.test_column_mode))

    def quit_confirm(self):
        if self.video_files_is_dirty:
            with curses_gui.MessagePanel(['Video data has been updated but not saved']) as message_panel:
                message_panel.run()
            return False
        else:
            return True

    # @staticmethod
    # def test_column_mode():
    #     display_lines = [curses_gui.Row(['1', 'One']), curses_gui.Row(['2', 'Twwwwwwwwwwwwwwwoooo']), curses_gui.Row(['333333333333', 'Three']), curses_gui.Row(['4', 'Four']), curses_gui.Row(['555', 'Five']), ]
    #     with curses_gui.ScrollingPanel(rows=display_lines, grid_mode=True, inner_padding=True) as scrolling_panel:
    #         scrolling_panel.run()

    @staticmethod
    def test_column_mode():
        import random
        import string

        display_lines = list()
        for row_i in range(100):
            text_list = list()
            for col_i in range(2):
                text_len = random.randint(5, 15)
                text = ''
                for text_i in range(text_len):
                    text += random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits + '      ')
                text_list.append(text)
            display_lines.append(text_list)
        header_columns = list()
        header_columns.append(curses_gui.Column('Header Column 1', colour=curses_gui.CursesColourBinding.COLOUR_BLACK_RED))
        header_columns.append(curses_gui.Column('Header Column 2', colour=curses_gui.CursesColourBinding.COLOUR_BLACK_RED))
        header_row = curses_gui.Row(columns=header_columns)
        with curses_gui.ScrollingPanel(rows=display_lines, grid_mode=True, inner_padding=True, header_row=header_row) as scrolling_panel:
            scrolling_panel.run()

    def update_video_imdb_info(self, video_file: imdb_utils.VideoFile):
        imdb_search_response = imdb_utils.get_imdb_search_results(video_file.scrubbed_file_name, video_file.year)
        imdb_info_list = imdb_utils.parse_imdb_search_results(imdb_search_response)

        header_columns = [curses_gui.Column('IMDB REFNUM', colour=curses_gui.CursesColourBinding.COLOUR_BLACK_RED),
                          curses_gui.Column('IMDB NAME', colour=curses_gui.CursesColourBinding.COLOUR_BLACK_RED),
                          curses_gui.Column('IMDB YEAR', colour=curses_gui.CursesColourBinding.COLOUR_BLACK_RED)]
        header_row = curses_gui.Row(columns=header_columns)
        display_lines = [curses_gui.Row([imdb_info.imdb_tt, imdb_info.imdb_name, imdb_info.imdb_year]) for imdb_info in imdb_info_list]
        with curses_gui.ScrollingPanel(rows=display_lines, header_row=header_row, grid_mode=True, inner_padding=True) as imdb_search_results_panel:
            while True:
                run_result = imdb_search_results_panel.run()
                if run_result.key == curses_gui.Keycodes.ESCAPE:
                    break
                # elif run_result.key == curses_gui.Keycodes.RETURN and run_result.row_index == 0:
                #     self.update_video_imdb_info(video_file)
        self.video_files_is_dirty = True

    def display_individual_video_file(self, video_file: imdb_utils.VideoFile):
        json_str = json.dumps(dataclasses.asdict(video_file), indent=4, sort_keys=True)
        json_str_lines = json_str.splitlines()
        display_lines = ['Search IMDB', curses_gui.HorizontalLine()] + json_str_lines
        with curses_gui.ScrollingPanel(rows=display_lines, height=0.5, width=0.5) as video_info_panel:
            while True:
                run_result = video_info_panel.run()
                if run_result.key == curses_gui.Keycodes.ESCAPE:
                    break
                elif run_result.key == curses_gui.Keycodes.RETURN and run_result.row_index == 0:
                    self.update_video_imdb_info(video_file)

    def display_all_video_file_data(self):
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
            year_str = f'({video_file.year})' if video_file.year else ' ' * 6
            imdb_tt = video_file.imdb_tt

            info = f'[{i:0{num_digits}d}] {video_file.scrubbed_file_name:{max_len}} {year_str} {imdb_tt}]'
            video_info_lines.append(info)

        with curses_gui.ScrollingPanel(rows=video_info_lines) as scrolling_panel:
            while True:
                run_result = scrolling_panel.run()
                if run_result.key == curses_gui.Keycodes.ESCAPE:
                    break
                elif run_result.key == curses_gui.Keycodes.RETURN:
                    video_file = self.video_files[run_result.row_index]
                    self.display_individual_video_file(video_file)

    def save_video_file_data(self):
        if not self.video_files:
            final_message = 'No video info to save'

        else:
            final_message = 'Video data not saved'

            with curses_gui.InputPanel(prompt='Enter path to video file data: ', default_value=self.video_file_path) as input_panel:
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
        with curses_gui.InputPanel(prompt='Enter path to video file data: ', default_value=self.video_file_path) as input_panel:
            video_file_path = input_panel.run()
        if video_file_path is None:
            return

        self.video_file_path = video_file_path

        with open(self.video_file_path, encoding='utf8') as f:
            video_files_json = json.load(f)

        self.video_files_is_dirty = False

        self.video_files = list()
        for video_file_dict in video_files_json:
            video_file = imdb_utils.VideoFile(**video_file_dict)
            self.video_files.append(video_file)

        with curses_gui.MessagePanel([f'Loaded video file date from {self.video_file_path}']) as message_panel:
            message_panel.run()

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

        self.display_all_video_file_data()


# For Pycharm "Attach to Process" execute: sudo sysctl kernel.yama.ptrace_scope=0

if __name__ == '__main__':
    logging.basicConfig(filename='/tmp/imdb_scraper.log', format='[%(process)d]:%(levelname)s:%(funcName)s:%(lineno)d: %(message)s', level=logging.INFO)

    logging.info('Starting up...')
    curses_gui.console_gui_main(MyMenu)
    logging.info('Ending.')
