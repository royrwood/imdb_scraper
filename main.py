#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import dataclasses
import functools
import logging
import json
import math
import textwrap
from typing import List, Optional

import imdb_scraper.imdb_utils
from imdb_scraper import curses_gui
from imdb_scraper import imdb_utils


class VideoFileEditor:
    def __init__(self, video_file: imdb_utils.VideoFile, imdb_search_results: List[imdb_utils.IMDBInfo] = None):
        self.video_file = video_file
        self.display_lines = list()

        if imdb_search_results:
            self.imdb_search_results: List[Optional[imdb_utils.IMDBInfo]] = imdb_search_results
            self.imdb_search_results_selected_index = 0
            self.hilighted_row = 3
        else:
            self.imdb_search_results: List[Optional[imdb_utils.IMDBInfo]] = list()
            self.imdb_search_results_selected_index = None
            self.hilighted_row = None

        self.imdb_search_results_start_row = -1
        self.imdb_search_results_end_row = -1
        self.video_info_json_start_row = -1
        self.video_info_json_end_row = -1

    def perform_edit_action(self, row_index: int):
        self.hilighted_row = None

        if row_index == 0 or row_index == 1:
            ask_for_name = bool(row_index == 1)
            try:
                self.do_imdb_search_and_load_detail(self.video_file.scrubbed_file_name, self.video_file.scrubbed_file_year, ask_for_name=ask_for_name)
            except curses_gui.UserCancelException:
                logging.info('User cancelled IMDB search/detail fetch')

        elif self.imdb_search_results and self.imdb_search_results_start_row <= row_index < self.imdb_search_results_end_row:
            current_imdb_selected_detail_index = self.imdb_search_results_selected_index
            new_imdb_selected_detail_index = row_index - self.imdb_search_results_start_row
            new_imdb_search_result = self.imdb_search_results[new_imdb_selected_detail_index]
            new_imdb_search_result_is_loaded = new_imdb_search_result.imdb_year or new_imdb_search_result.imdb_rating or new_imdb_search_result.imdb_genres or new_imdb_search_result.imdb_plot

            if new_imdb_selected_detail_index == current_imdb_selected_detail_index:
                self.set_video_file_to_currently_selected_imdb_detail_result()
            elif new_imdb_search_result_is_loaded:
                self.imdb_search_results_selected_index = new_imdb_selected_detail_index
            else:
                try:
                    self.load_imdb_detail_info(new_imdb_selected_detail_index)
                    self.imdb_search_results_selected_index = new_imdb_selected_detail_index
                except curses_gui.UserCancelException:
                    logging.info('User cancelled IMDB search/detail fetch')

    def set_video_file_to_currently_selected_imdb_detail_result(self):
        imdb_detail_result = self.imdb_search_results[self.imdb_search_results_selected_index]
        self.video_file.imdb_tt = imdb_detail_result.imdb_tt
        self.video_file.imdb_rating = imdb_detail_result.imdb_rating
        self.video_file.imdb_name = imdb_detail_result.imdb_name
        self.video_file.imdb_year = imdb_detail_result.imdb_year
        self.video_file.imdb_genres = imdb_detail_result.imdb_genres
        self.video_file.imdb_plot = imdb_detail_result.imdb_plot
        self.video_file.is_dirty = True

    def load_imdb_search_info(self, file_name: str, file_year = ''):
        dialog_msg = f'Fetching IMDB Search Info for "{file_name}"'
        imdb_search_task = functools.partial(imdb_utils.get_parse_imdb_search_results, file_name, file_year)
        if not (imdb_search_results := curses_gui.run_cancellable_thread_dialog(imdb_search_task, dialog_msg)):
            with curses_gui.DialogBox(prompt=[f'No search results for "{file_name}"'], buttons_text=['OK']) as dialog_box:
                dialog_box.run()
            return

        self.imdb_search_results = imdb_search_results

    def load_imdb_detail_info(self, imdb_info_index: int):
        imdb_info = self.imdb_search_results[imdb_info_index]

        dialog_msg = f'Fetching IMDB Detail Info for "{imdb_info.imdb_name}"'
        imdb_details_task = functools.partial(imdb_utils.get_parse_imdb_tt_info, imdb_info.imdb_tt)
        if not (imdb_detail_result := curses_gui.run_cancellable_thread_dialog(imdb_details_task, dialog_msg)):
            with curses_gui.DialogBox(prompt=[f'No detail results for "{imdb_info.imdb_name}"'], buttons_text=['OK']) as dialog_box:
                dialog_box.run()
            return

        self.imdb_search_results[imdb_info_index] = imdb_detail_result

    def do_imdb_search_and_load_detail(self, file_name: str, file_year ='', ask_for_name = False):
        if ask_for_name:
            file_year = None

            with curses_gui.InputPanel(prompt='Enter IMDB search target: ', default_value=file_name) as input_panel:
                file_name = input_panel.run()

            if file_name is None:
                return

        self.load_imdb_search_info(file_name, file_year)
        if self.imdb_search_results:
            self.load_imdb_detail_info(0)
            self.imdb_search_results_selected_index = 0
            self.hilighted_row = 3

    def setup_display_lines(self, panel_width: int, panel_height: int) -> List:
        self.display_lines = list()

        if self.video_file.scrubbed_file_year:
            self.display_lines.append(f'Search IMDB for "{self.video_file.scrubbed_file_name} ({self.video_file.scrubbed_file_year})"')
        else:
            self.display_lines.append(f'Search IMDB for "{self.video_file.scrubbed_file_name}"')

        self.display_lines.append(f'Search IMDB for other target')

        self.display_lines.append(curses_gui.HorizontalLine())

        if self.imdb_search_results:
            max_name_length = 0
            max_tt_length = 0
            for i in range(len(self.imdb_search_results)):
                imdb_info = self.imdb_search_results[i]
                max_name_length = max(max_name_length, len(imdb_info.imdb_name))
                max_tt_length = max(max_tt_length, len(imdb_info.imdb_tt))
            max_name_length = min(max_name_length, 75)

            self.imdb_search_results_start_row = len(self.display_lines)
            for i in range(len(self.imdb_search_results)):
                imdb_info = self.imdb_search_results[i]
                if i == self.imdb_search_results_selected_index:
                    self.display_lines.append(f'=> {imdb_info.imdb_tt:{max_tt_length}} {imdb_info.imdb_name[:max_name_length]: <{max_name_length}}  [{imdb_info.imdb_year[:4]: <4}] [{imdb_info.imdb_rating: <3}] {imdb_info.imdb_plot}')
                else:
                    self.display_lines.append(f'   {imdb_info.imdb_tt:{max_tt_length}} {imdb_info.imdb_name[:max_name_length]: <{max_name_length}}  [{imdb_info.imdb_year[:4]: <4}] [{imdb_info.imdb_rating: <3}] {imdb_info.imdb_plot}')
            self.imdb_search_results_end_row = len(self.display_lines)

            self.display_lines.append(curses_gui.HorizontalLine())

        if self.imdb_search_results_selected_index is not None and self.imdb_search_results[self.imdb_search_results_selected_index].imdb_name:
            imdb_info = self.imdb_search_results[self.imdb_search_results_selected_index]

            # self.imdb_detail_results_start_row = len(self.display_lines)

            self.display_lines.append(f'imdb_name:   {imdb_info.imdb_name}')
            self.display_lines.append(f'imdb_rating: {imdb_info.imdb_rating}')
            self.display_lines.append(f'imdb_year:   {imdb_info.imdb_year}')
            self.display_lines.append(f'imdb_tt:     {imdb_info.imdb_tt}')
            self.display_lines.append(f'imdb_genres: {imdb_info.imdb_genres}')

            wrap_width = min(panel_width - 20, 100)
            plot_lines = textwrap.wrap(imdb_info.imdb_plot, width=wrap_width) or ['']
            self.display_lines.append(f'')
            self.display_lines.append(f'imdb_plot:   {plot_lines[0]}')
            for plot_line in plot_lines[1:]:
                self.display_lines.append(f'             {plot_line}')

            # self.imdb_detail_results_end_row = len(self.display_lines)

        else:
            json_str = json.dumps(dataclasses.asdict(self.video_file), indent=4, sort_keys=True)
            json_str_lines = json_str.splitlines()
            self.video_info_json_start_row = len(self.display_lines)
            self.display_lines.extend(json_str_lines)
            self.video_info_json_end_row = len(self.display_lines)

        return self.display_lines

def edit_individual_video_file(video_file: imdb_utils.VideoFile, imdb_search_results: List[imdb_utils.IMDBInfo] = None):
    video_file.is_dirty = False
    video_file_editor = VideoFileEditor(video_file, imdb_search_results)

    with curses_gui.ScrollingPanel(rows=[''], height=0.75, width=0.75, hilighted_row_index=video_file_editor.hilighted_row) as video_panel:
        while True:
            panel_width, panel_height = video_panel.get_width_height()
            video_file_editor.setup_display_lines(panel_width, panel_height)
            video_panel.set_rows(video_file_editor.display_lines, hilighted_row=video_file_editor.hilighted_row)
            video_panel.show()

            run_result = video_panel.run()

            if run_result.key == curses_gui.Keycodes.ESCAPE:
                raise curses_gui.UserCancelException()
            else:
                video_file_editor.perform_edit_action(run_result.row_index)

                if video_file.is_dirty:
                    return video_file


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

        self.menu_choices.append((curses_gui.HorizontalLine(), None))
        self.menu_choices.append(('test_message_panel', self.test_message_panel))

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


    @staticmethod
    def test_message_panel():
        with curses_gui.MessagePanel(['This is a test'], height=0.5) as message_panel:
            for i in range(100):
                message_panel.append_message_lines(f'Line {i}', trim_to_visible_window=True)
            message_panel.run()


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

    def display_all_video_file_data(self):
        if not self.video_files:
            with curses_gui.DialogBox(prompt=['No video files to process'], buttons_text=['OK']) as dialog_box:
                dialog_box.run()
            return

        header_columns = [curses_gui.Column('', colour=curses_gui.CursesColourBinding.COLOUR_CYAN_BLACK),
                          curses_gui.Column('NAME', colour=curses_gui.CursesColourBinding.COLOUR_CYAN_BLACK),
                          curses_gui.Column('YEAR', colour=curses_gui.CursesColourBinding.COLOUR_CYAN_BLACK),
                          curses_gui.Column('RATING', colour=curses_gui.CursesColourBinding.COLOUR_CYAN_BLACK),
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
                        display_rows.append(curses_gui.Row([f'[{i:0{num_digits}d}]', video_file.imdb_name, video_file.imdb_year, f'{video_file.imdb_rating}', f'[{video_file.imdb_tt}]', video_file.file_path]))
                    else:
                        display_rows.append(curses_gui.Row([f'[{i:0{num_digits}d}]', video_file.scrubbed_file_name, video_file.scrubbed_file_year, '', '', video_file.file_path]))
                hilighted_row_index = scrolling_panel.hilighted_row_index
                top_visible_row_index = scrolling_panel.top_visible_row_index
                scrolling_panel.set_rows(display_rows)
                scrolling_panel.set_hilighted_row(hilighted_row_index, top_visible_row_index)
                scrolling_panel.show()

                run_result = scrolling_panel.run()
                if run_result.key == curses_gui.Keycodes.ESCAPE:
                    break
                elif run_result.key == curses_gui.Keycodes.RETURN:
                    scrolling_panel.hide()

                    selected_video_file = self.video_files[run_result.row_index]
                    try:
                        edit_individual_video_file(selected_video_file)
                        if selected_video_file.is_dirty:
                            self.video_files_is_dirty = True
                    except curses_gui.UserCancelException:
                        logging.info('User cancelled video file edit')

    def save_video_file_data(self):
        if not self.video_files:
            with curses_gui.DialogBox(prompt=['No video info to save']) as dialog_box:
                dialog_box.run()
            return

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

        with curses_gui.DialogBox(prompt=[final_message]) as dialog_box:
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

        num_video_files = len(self.video_files)
        with curses_gui.DialogBox(prompt=[f'Loaded {num_video_files} video files from "{self.video_file_path}"'], buttons_text=['OK']) as dialog_box:
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

    def update_all_video_file_data(self):
        if not self.video_files:
            with curses_gui.DialogBox(prompt=['No video files to process'], buttons_text=['OK']) as dialog_box:
                dialog_box.run()
            return

        unprocessed_video_files = [video_file for video_file in self.video_files if not video_file.imdb_tt]
        num_video_files = len(unprocessed_video_files)
        num_video_files_processed = 0

        with curses_gui.MessagePanel(['Beginning processing of video files...'], height=0.25) as message_panel:
            for i, video_file in enumerate(unprocessed_video_files):
                progress_message = f'Processing {video_file.scrubbed_file_name} [{i}/{num_video_files}]'
                message_panel.append_message_lines(progress_message, trim_to_visible_window=True)

                try:
                    message_panel.append_message_lines(f'Searching IMDB for {video_file.scrubbed_file_name} [{i}/{num_video_files}]', trim_to_visible_window=True)
                    imdb_search_results = curses_gui.run_cancellable_thread(functools.partial(imdb_utils.get_parse_imdb_search_results, video_file.scrubbed_file_name, video_file.scrubbed_file_year), getch_function=message_panel.window.getch)
                    message_panel.append_message_lines(f'Found IMDB {len(imdb_search_results)} results for {video_file.scrubbed_file_name} [{i}/{num_video_files}]', trim_to_visible_window=True)

                    if imdb_search_results and imdb_search_results[0].imdb_tt:
                        imdb_tt = imdb_search_results[0].imdb_tt
                        message_panel.append_message_lines(f'Fetching IMDB details for {imdb_tt} [{i}/{num_video_files}]', trim_to_visible_window=True)
                        imdb_search_results[0] = curses_gui.run_cancellable_thread(functools.partial(imdb_utils.get_parse_imdb_tt_info, imdb_tt), getch_function=message_panel.window.getch)
                        message_panel.append_message_lines(f'Fetched IMDB details for {imdb_tt} [{i}/{num_video_files}]', trim_to_visible_window=True)

                    edit_individual_video_file(video_file, imdb_search_results=imdb_search_results)

                    self.video_files_is_dirty = video_file.is_dirty or self.video_files_is_dirty

                    num_video_files_processed += 1

                except curses_gui.UserCancelException:
                    with curses_gui.DialogBox(prompt=['Continue processing or Cancel?'], buttons_text=['Continue', 'Cancel']) as dialog_box:
                        if dialog_box.run() == 'Cancel':
                            break

                message_panel.append_message_lines(curses_gui.HorizontalLine())

        with curses_gui.DialogBox(prompt=[f'Processed {num_video_files_processed} video files']) as dialog_box:
            dialog_box.run()


# For Pycharm "Attach to Process" execute: sudo sysctl kernel.yama.ptrace_scope=0

if __name__ == '__main__':
    logging.basicConfig(filename='/tmp/imdb_scraper.log', format='[%(process)d]:%(levelname)s:%(funcName)s:%(lineno)d: %(message)s', level=logging.INFO)

    logging.info('Starting up...')
    curses_gui.console_gui_main(MyMenu)
    logging.info('Ending.')
