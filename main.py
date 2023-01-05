#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import dataclasses
import functools
import logging
import json
import math
import traceback
from typing import List, Optional, Tuple

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
        self.menu_choices.append(('Update Video Info', self.update_all_video_file_data))
        # self.menu_choices.append((curses_gui.HorizontalLine(), None))
        # self.menu_choices.append(('test_scrolling_panel_grid_mode', self.test_scrolling_panel))
        # self.menu_choices.append(('test_scrolling_panel_select_grid_cells', self.test_scrolling_panel_select_grid_cells))
        # self.menu_choices.append(('test_scrolling_panel_100_rows', self.test_scrolling_panel_100_rows))
        # self.menu_choices.append(('test_scrolling_panel_width', self.test_scrolling_panel_width))
        # self.menu_choices.append(('test_scrolling_panel_width_height', self.test_scrolling_panel_width_height))

    def quit_confirm(self):
        if self.video_files_is_dirty:
            with curses_gui.MessagePanel(['Video data has been updated but not saved']) as message_panel:
                message_panel.run()
            return False
        else:
            return True

    # @staticmethod
    # def test_scrolling_panel_width_height():
    #     header_columns = list()
    #     header_columns.append(curses_gui.Column('Header Column 1', colour=curses_gui.CursesColourBinding.COLOUR_CYAN_BLACK))
    #     header_columns.append(curses_gui.Column('Header Column 2', colour=curses_gui.CursesColourBinding.COLOUR_CYAN_BLACK))
    #     header_row = curses_gui.Row(header_columns)
    #
    #     display_lines = [curses_gui.Row(['1', 'One']),
    #                      curses_gui.Row(['2', 'Twwwwwwwwwwwwwwwoooo']),
    #                      curses_gui.Row(['333333333333', 'Three']),
    #                      curses_gui.Row(['4', 'Four']),
    #                      curses_gui.HorizontalLine(),
    #                      curses_gui.Row(['555', 'Five']), ]
    #     with curses_gui.ScrollingPanel(rows=display_lines, header_row=header_row, width=0.5, height=0.5, inner_padding=True) as scrolling_panel:
    #         scrolling_panel.run()
    #
    # @staticmethod
    # def test_scrolling_panel_width():
    #     header_columns = list()
    #     header_columns.append(curses_gui.Column('Header Column 1', colour=curses_gui.CursesColourBinding.COLOUR_CYAN_BLACK))
    #     header_columns.append(curses_gui.Column('Header Column 2', colour=curses_gui.CursesColourBinding.COLOUR_CYAN_BLACK))
    #     header_row = curses_gui.Row(header_columns)
    #
    #     display_lines = [curses_gui.Row(['1', 'One']),
    #                      curses_gui.Row(['2', 'Twwwwwwwwwwwwwwwoooo']),
    #                      curses_gui.Row(['333333333333', 'Three']),
    #                      curses_gui.Row(['4', 'Four']),
    #                      curses_gui.HorizontalLine(),
    #                      curses_gui.Row(['555', 'Five']), ]
    #     with curses_gui.ScrollingPanel(rows=display_lines, header_row=header_row, width=25, height=20, inner_padding=True) as scrolling_panel:
    #         scrolling_panel.run()
    #
    # @staticmethod
    # def test_scrolling_panel():
    #     display_lines = [curses_gui.Row(['1', 'One']),
    #                      curses_gui.Row(['2', 'Twwwwwwwwwwwwwwwoooo']),
    #                      curses_gui.Row(['333333333333', 'Three']),
    #                      curses_gui.Row(['4', 'Four']),
    #                      curses_gui.HorizontalLine(),
    #                      curses_gui.Row(['555', 'Five']), ]
    #     with curses_gui.ScrollingPanel(rows=display_lines, inner_padding=True) as scrolling_panel:
    #         scrolling_panel.run()
    #
    # @staticmethod
    # def test_scrolling_panel_select_grid_cells():
    #     display_lines = [curses_gui.Row(['1', 'One']),
    #                      curses_gui.Row(['2', 'Twwwwwwwwwwwwwwwoooo']),
    #                      curses_gui.Row(['333333333333', 'Three']),
    #                      curses_gui.Row(['4', 'Four']),
    #                      curses_gui.HorizontalLine(),
    #                      curses_gui.Row(['555', 'Five']), ]
    #     with curses_gui.ScrollingPanel(rows=display_lines, inner_padding=True, select_grid_cells=True) as scrolling_panel:
    #         scrolling_panel.run()
    #
    # @staticmethod
    # def test_scrolling_panel_100_rows():
    #     import random
    #     import string
    #
    #     display_lines = list()
    #     for row_i in range(100):
    #         text_list = list()
    #         for col_i in range(2):
    #             text_len = random.randint(5, 15)
    #             text = ''
    #             for text_i in range(text_len):
    #                 text += random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits + '      ')
    #             text_list.append(text)
    #         display_lines.append(text_list)
    #     header_columns = list()
    #     header_columns.append(curses_gui.Column('Header Column 1', colour=curses_gui.CursesColourBinding.COLOUR_CYAN_BLACK))
    #     header_columns.append(curses_gui.Column('Header Column 2', colour=curses_gui.CursesColourBinding.COLOUR_CYAN_BLACK))
    #     header_row = curses_gui.Row(header_columns)
    #     with curses_gui.ScrollingPanel(rows=display_lines, inner_padding=True, header_row=header_row) as scrolling_panel:
    #         scrolling_panel.run()

    @staticmethod
    def show_exception_details(exc_type, exc_value, exc_traceback):
        message_lines = [f'Caught an exception: {exc_value}']
        exception_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        for exception_line in exception_lines:
            for line in exception_line.split('\n'):
                if line.strip():
                    message_lines.append(line)

        for line in message_lines:
            logging.error(line)

        with curses_gui.MessagePanel(message_lines) as message_panel:
            message_panel.run()
            return

    def get_imdb_detail_info(self, imdb_tt: str) -> Optional[imdb_utils.IMDBInfo]:
        imdb_details_task = functools.partial(imdb_utils.get_parse_imdb_tt_info, imdb_tt)
        threaded_dialog_result = curses_gui.run_cancellable_thread_dialog(imdb_details_task, 'Fetching IMDB Detail Info...')
        if threaded_dialog_result.dialog_result is not None:
            return None

        if threaded_dialog_result.selectable_thread.callable_exception_info_tuple:
            exc_type, exc_value, exc_traceback = threaded_dialog_result.selectable_thread.callable_exception_info_tuple
            self.show_exception_details(exc_type, exc_value, exc_traceback)
            return None

        return threaded_dialog_result.selectable_thread.callable_result

    def get_imdb_search_info(self, file_name, file_year) -> List[imdb_utils.IMDBInfo]:
        imdb_search_task = functools.partial(imdb_utils.get_parse_imdb_search_results, file_name, file_year)
        threaded_dialog_result = curses_gui.run_cancellable_thread_dialog(imdb_search_task, f'Fetching IMDB Search Info for "{file_name}"...')
        if threaded_dialog_result.dialog_result is not None:
            return []

        if threaded_dialog_result.selectable_thread.callable_exception_info_tuple:
            exc_type, exc_value, exc_traceback = threaded_dialog_result.selectable_thread.callable_exception_info_tuple
            self.show_exception_details(exc_type, exc_value, exc_traceback)
            return []

        return threaded_dialog_result.selectable_thread.callable_result

    @staticmethod
    def setup_individual_video_file_display_lines(video_file: imdb_utils.VideoFile, imdb_search_results: List[imdb_utils.IMDBInfo], imdb_detail_results: List[imdb_utils.IMDBInfo]) -> Tuple[List[str], int, int]:
        display_lines = ['Search IMDB', curses_gui.HorizontalLine()]
        imdb_detail_start_row = len(display_lines)
        imdb_detail_end_row = imdb_detail_start_row + len(imdb_search_results)

        if imdb_search_results:
            max_name_length = 0
            max_tt_length = 0
            for i in range(len(imdb_search_results)):
                imdb_info = imdb_detail_results[i] or imdb_search_results[i]
                max_name_length = max(max_name_length, len(imdb_info.imdb_name))
                max_tt_length = max(max_tt_length, len(imdb_info.imdb_tt))

            max_name_length = min(max_name_length, 75)

            for i in range(len(imdb_search_results)):
                imdb_info = imdb_detail_results[i] or imdb_search_results[i]
                imdb_info_str = f'{imdb_info.imdb_tt:{max_tt_length}} {imdb_info.imdb_name[:max_name_length]: <{max_name_length}}  [{imdb_info.imdb_year[:4]: <4}] [{imdb_info.imdb_rating: <3}] {imdb_info.imdb_plot}'
                display_lines.append(imdb_info_str)
            display_lines.append(curses_gui.HorizontalLine())

        json_str = json.dumps(dataclasses.asdict(video_file), indent=4, sort_keys=True)
        json_str_lines = json_str.splitlines()

        display_lines.extend(json_str_lines)

        return display_lines, imdb_detail_start_row, imdb_detail_end_row

    def setup_search_results_detail_results(self, video_file: imdb_utils.VideoFile, auto_search: bool) -> Tuple[List[Optional[imdb_utils.IMDBInfo]], List[Optional[imdb_utils.IMDBInfo]]]:
        if not auto_search:
            return [], []

        imdb_search_results = self.get_imdb_search_info(video_file.scrubbed_file_name, video_file.scrubbed_file_year)
        imdb_detail_results = [None] * len(imdb_search_results)

        if imdb_search_results and (imdb_search_result := imdb_search_results[0]):
            if imdb_detail_result := self.get_imdb_detail_info(imdb_search_result.imdb_tt):
                imdb_detail_results[0] = imdb_detail_result

        return imdb_search_results, imdb_detail_results

    def display_individual_video_file(self, video_file: imdb_utils.VideoFile, auto_search=False):
        imdb_search_results, imdb_detail_results = self.setup_search_results_detail_results(video_file, auto_search)

        with curses_gui.ScrollingPanel(rows=[''], height=0.75, width=0.75) as video_info_panel:
            while True:
                display_lines, imdb_detail_start_row, imdb_detail_end_row = self.setup_individual_video_file_display_lines(video_file, imdb_search_results, imdb_detail_results)

                video_info_panel.set_rows(display_lines)
                if auto_search and imdb_detail_results:
                    video_info_panel.set_hilighted_row(imdb_detail_start_row)
                    auto_search = False
                video_info_panel.show()

                run_result = video_info_panel.run()
                if run_result.key == curses_gui.Keycodes.ESCAPE:
                    return None

                elif run_result.key == curses_gui.Keycodes.RETURN and run_result.row_index == 0:
                    imdb_search_results, imdb_detail_results = self.setup_search_results_detail_results(video_file, True)
                    video_info_panel.set_hilighted_row(imdb_detail_start_row)

                elif run_result.key == curses_gui.Keycodes.RETURN and imdb_detail_start_row <= run_result.row_index < imdb_detail_end_row:
                    imdb_search_index = run_result.row_index - imdb_detail_start_row
                    imdb_search_result = imdb_search_results[imdb_search_index]
                    imdb_detail_result = imdb_detail_results[imdb_search_index]

                    if (imdb_detail_result is None) and (imdb_detail_result := self.get_imdb_detail_info(imdb_search_result.imdb_tt)):
                        imdb_detail_results[imdb_search_index] = imdb_detail_result
                        continue

                    if imdb_detail_result:
                        video_file.imdb_tt = imdb_detail_result.imdb_tt
                        video_file.imdb_rating = imdb_detail_result.imdb_rating
                        video_file.imdb_name = imdb_detail_result.imdb_name
                        video_file.imdb_year = imdb_detail_result.imdb_year
                        video_file.imdb_genres = imdb_detail_result.imdb_genres
                        video_file.imdb_plot = imdb_detail_result.imdb_plot
                        self.video_files_is_dirty = True

                        return video_file

    def display_all_video_file_data(self):
        header_columns = [curses_gui.Column('', colour=curses_gui.CursesColourBinding.COLOUR_CYAN_BLACK),
                          curses_gui.Column('NAME', colour=curses_gui.CursesColourBinding.COLOUR_CYAN_BLACK),
                          curses_gui.Column('YEAR', colour=curses_gui.CursesColourBinding.COLOUR_CYAN_BLACK),
                          curses_gui.Column('IMDB-TT', colour=curses_gui.CursesColourBinding.COLOUR_CYAN_BLACK),
                          curses_gui.Column('FILE PATH', colour=curses_gui.CursesColourBinding.COLOUR_CYAN_BLACK),
                          ]
        header_row = curses_gui.Row(header_columns)

        with curses_gui.ScrollingPanel(rows=[''], header_row=header_row, inner_padding=True, show_immediately=False) as scrolling_panel:
            while True:
                num_video_files = len(self.video_files)
                num_digits = math.floor(math.log10(num_video_files)) + 1
                display_rows = []
                for i, video_file in enumerate(self.video_files):
                    if video_file.imdb_tt:
                        display_rows.append(curses_gui.Row([f'[{i:0{num_digits}d}]', video_file.imdb_name, video_file.imdb_year, f'[{video_file.imdb_tt}]', video_file.file_path]))
                    else:
                        display_rows.append(curses_gui.Row([f'[{i:0{num_digits}d}]', video_file.scrubbed_file_name, video_file.scrubbed_file_year, f'[{video_file.imdb_tt}]', video_file.file_path]))
                scrolling_panel.set_rows(display_rows)
                scrolling_panel.show()

                run_result = scrolling_panel.run()
                if run_result.key == curses_gui.Keycodes.ESCAPE:
                    break
                elif run_result.key == curses_gui.Keycodes.RETURN:
                    scrolling_panel.hide()

                    selected_video_file = self.video_files[run_result.row_index]
                    self.display_individual_video_file(selected_video_file)

    def update_all_video_file_data(self):
        for i, video_file in enumerate(self.video_files):
            if video_file.imdb_tt:
                continue

            if not self.display_individual_video_file(video_file, True):
                with curses_gui.DialogBox(prompt=[f'Continue processing?'], buttons_text=['Continue', 'Cancel']) as dialog_box:
                    if dialog_box.run() != 'Continue':
                        break

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
                final_message = f'Video saved to "{video_file_path}"'
                self.video_files_is_dirty = False

        with curses_gui.DialogBox(prompt=[final_message], buttons_text=['OK']) as dialog_box:
            dialog_box.run()

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

        with curses_gui.DialogBox(prompt=[f'Loaded video file date from "{self.video_file_path}"'], buttons_text=['OK']) as dialog_box:
            dialog_box.run()

    def scan_video_folder(self):
        with curses_gui.InputPanel(prompt='Enter path to folder: ', default_value='/home/rrwood/Videos/Movies/') as input_panel:
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
