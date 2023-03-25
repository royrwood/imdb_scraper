#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import dataclasses
import functools
import logging
import json
import math
import textwrap
import traceback
from typing import List, Optional, Tuple

import imdb_scraper.imdb_utils
from imdb_scraper import curses_gui
from imdb_scraper import imdb_utils


class UserCancelException(Exception):
    pass


class AsyncThreadException(Exception):
    pass


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

def get_imdb_detail_info(imdb_info: imdb_utils.IMDBInfo, dialog_msg_suffix: str = '') -> Optional[imdb_utils.IMDBInfo]:
    dialog_msg = f'Fetching IMDB Detail Info for "{imdb_info.imdb_name}"{dialog_msg_suffix}'
    imdb_details_task = functools.partial(imdb_utils.get_parse_imdb_tt_info, imdb_info.imdb_tt)
    threaded_dialog_result = curses_gui.run_cancellable_thread_dialog(imdb_details_task, dialog_msg)
    if threaded_dialog_result.dialog_result is not None:
        raise UserCancelException()

    if threaded_dialog_result.selectable_thread.callable_exception_info_tuple:
        exc_type, exc_value, exc_traceback = threaded_dialog_result.selectable_thread.callable_exception_info_tuple
        show_exception_details(exc_type, exc_value, exc_traceback)
        raise AsyncThreadException()

    return threaded_dialog_result.selectable_thread.callable_result

def get_imdb_search_info(file_name, file_year, dialog_msg_suffix: str = '') -> List[imdb_utils.IMDBInfo]:
    dialog_msg = f'Fetching IMDB Search Info for "{file_name}"{dialog_msg_suffix}'
    imdb_search_task = functools.partial(imdb_utils.get_parse_imdb_search_results, file_name, file_year)
    threaded_dialog_result = curses_gui.run_cancellable_thread_dialog(imdb_search_task, dialog_msg)
    if threaded_dialog_result.dialog_result is not None:
        raise UserCancelException()

    if threaded_dialog_result.selectable_thread.callable_exception_info_tuple:
        exc_type, exc_value, exc_traceback = threaded_dialog_result.selectable_thread.callable_exception_info_tuple
        show_exception_details(exc_type, exc_value, exc_traceback)
        raise AsyncThreadException()

    return threaded_dialog_result.selectable_thread.callable_result


def setup_video_file_edit_body(video_file: imdb_utils.VideoFile, imdb_detail_results: List[imdb_utils.IMDBInfo], imdb_selected_detail_index: Optional[int], panel_width: int) -> List:
    display_lines = []

    if imdb_selected_detail_index is not None and imdb_detail_results and imdb_detail_results[imdb_selected_detail_index]:
        imdb_info = imdb_detail_results[imdb_selected_detail_index]

        imdb_detail_lines = list()
        imdb_detail_lines.append(f'imdb_tt:     {imdb_info.imdb_name}')
        imdb_detail_lines.append(f'imdb_rating: {imdb_info.imdb_rating}')
        imdb_detail_lines.append(f'imdb_year:   {imdb_info.imdb_year}')
        imdb_detail_lines.append(f'imdb_tt:     {imdb_info.imdb_tt}')
        imdb_detail_lines.append(f'imdb_genres: {imdb_info.imdb_genres}')

        wrap_width = min(panel_width - 20, 100)
        plot_lines = textwrap.wrap(imdb_info.imdb_plot, width=wrap_width) or ['']
        imdb_detail_lines.append(f'')
        imdb_detail_lines.append(f'imdb_plot:   {plot_lines[0]}')
        for plot_line in plot_lines[1:]:
            imdb_detail_lines.append(f'             {plot_line}')

        display_lines.extend(imdb_detail_lines)

    else:
        json_str = json.dumps(dataclasses.asdict(video_file), indent=4, sort_keys=True)
        json_str_lines = json_str.splitlines()
        display_lines.extend(json_str_lines)

    return display_lines


class VideoFileEdit:
    def __init__(self, video_file: imdb_utils.VideoFile, additional_commands: List[str] = None):
        self.video_file = video_file
        self.additional_commands = additional_commands

        self.imdb_search_results: List[Optional[imdb_utils.IMDBInfo]] = list()
        self.imdb_detail_results: List[Optional[imdb_utils.IMDBInfo]] = list()
        self.imdb_selected_detail_index = None
        self.video_panel_hilited_row = None

        self.display_lines = list()
        self.additional_command_start_row = -1
        self.additional_command_end_row = -1
        self.imdb_search_results_start_row = -1
        self.imdb_search_results_end_row = -1
        self.imdb_detail_results_start_row = -1
        self.imdb_detail_results_end_row = -1
        self.video_info_json_start_row = -1
        self.video_info_json_end_row = -1


    def load_imdb_search_info(self, file_name: str, file_year = '', dialog_msg_suffix = ''):
        self.imdb_search_results = list()
        self.imdb_detail_results = list()

        dialog_msg = f'Fetching IMDB Search Info for "{file_name}"{dialog_msg_suffix}'
        imdb_search_task = functools.partial(imdb_utils.get_parse_imdb_search_results, file_name, file_year)
        threaded_dialog_result = curses_gui.run_cancellable_thread_dialog(imdb_search_task, dialog_msg)
        if threaded_dialog_result.dialog_result is not None:
            raise UserCancelException()

        if threaded_dialog_result.selectable_thread.callable_exception_info_tuple:
            exc_type, exc_value, exc_traceback = threaded_dialog_result.selectable_thread.callable_exception_info_tuple
            show_exception_details(exc_type, exc_value, exc_traceback)
            raise AsyncThreadException()

        self.imdb_search_results = threaded_dialog_result.selectable_thread.callable_result

        if not self.imdb_search_results:
            with curses_gui.DialogBox(prompt=[f'No search results for "{file_name}"'], buttons_text=['OK']) as dialog_box:
                dialog_box.run()
            return

        self.imdb_detail_results = [None] * len(self.imdb_search_results)

    def load_imdb_detail_info(self, imdb_info_index: int, dialog_msg_suffix = ''):
        imdb_info = self.imdb_search_results[imdb_info_index]

        dialog_msg = f'Fetching IMDB Detail Info for "{imdb_info.imdb_name}"{dialog_msg_suffix}'
        imdb_details_task = functools.partial(imdb_utils.get_parse_imdb_tt_info, imdb_info.imdb_tt)
        threaded_dialog_result = curses_gui.run_cancellable_thread_dialog(imdb_details_task, dialog_msg)
        if threaded_dialog_result.dialog_result is not None:
            raise UserCancelException()

        if threaded_dialog_result.selectable_thread.callable_exception_info_tuple:
            exc_type, exc_value, exc_traceback = threaded_dialog_result.selectable_thread.callable_exception_info_tuple
            show_exception_details(exc_type, exc_value, exc_traceback)
            raise AsyncThreadException()

        imdb_detail_result = threaded_dialog_result.selectable_thread.callable_result

        if not imdb_detail_result:
            with curses_gui.DialogBox(prompt=[f'No detail results for "{imdb_info.imdb_name}"'], buttons_text=['OK']) as dialog_box:
                dialog_box.run()
            return

        self.imdb_detail_results[imdb_info_index] = imdb_detail_result

    def do_search_and_load_detail(self, file_name: str, file_year = '', ask_for_name = False, dialog_msg_suffix = ''):
        if ask_for_name:
            file_year = None

            with curses_gui.InputPanel(prompt='Enter IMDB search target: ', default_value=file_name) as input_panel:
                file_name = input_panel.run()

            if file_name is None:
                return

        self.load_imdb_search_info(file_name, file_year, dialog_msg_suffix=dialog_msg_suffix)
        if self.imdb_search_results:
            self.load_imdb_detail_info(0, dialog_msg_suffix)
        if self.imdb_detail_results and self.imdb_detail_results[0]:
            self.imdb_selected_detail_index = 0

    def setup_display_lines(self, panel_width: int, panel_height: int) -> List:
        self.display_lines = list()

        if self.video_file.scrubbed_file_year:
            self.display_lines.append(f'Search IMDB for "{self.video_file.scrubbed_file_name} ({self.video_file.scrubbed_file_year})"')
        else:
            self.display_lines.append(f'Search IMDB for "{self.video_file.scrubbed_file_name}"')

        self.display_lines.append(f'Search IMDB for other target')

        if self.additional_commands:
            self.additional_command_start_row = len(self.display_lines)
            self.display_lines.extend(self.additional_commands)
            self.additional_command_end_row = len(self.display_lines)

        self.display_lines.append(curses_gui.HorizontalLine())

        if self.imdb_search_results:
            max_name_length = 0
            max_tt_length = 0
            for i in range(len(self.imdb_search_results)):
                imdb_info = self.imdb_detail_results[i] or self.imdb_search_results[i]
                max_name_length = max(max_name_length, len(imdb_info.imdb_name))
                max_tt_length = max(max_tt_length, len(imdb_info.imdb_tt))
            max_name_length = min(max_name_length, 75)

            self.imdb_search_results_start_row = len(self.display_lines)
            for i in range(len(self.imdb_search_results)):
                imdb_info = self.imdb_detail_results[i] or self.imdb_search_results[i]
                if i == self.imdb_selected_detail_index:
                    self.display_lines.append(f'=> {imdb_info.imdb_tt:{max_tt_length}} {imdb_info.imdb_name[:max_name_length]: <{max_name_length}}  [{imdb_info.imdb_year[:4]: <4}] [{imdb_info.imdb_rating: <3}] {imdb_info.imdb_plot}')
                else:
                    self.display_lines.append(f'   {imdb_info.imdb_tt:{max_tt_length}} {imdb_info.imdb_name[:max_name_length]: <{max_name_length}}  [{imdb_info.imdb_year[:4]: <4}] [{imdb_info.imdb_rating: <3}] {imdb_info.imdb_plot}')
            self.imdb_search_results_end_row = len(self.display_lines)

            self.display_lines.append(curses_gui.HorizontalLine())

        if self.imdb_selected_detail_index is not None and self.imdb_detail_results and self.imdb_detail_results[self.imdb_selected_detail_index]:
            imdb_info = self.imdb_detail_results[self.imdb_selected_detail_index]

            self.imdb_detail_results_start_row = len(self.display_lines)

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

            self.imdb_detail_results_end_row = len(self.display_lines)

        else:
            json_str = json.dumps(dataclasses.asdict(self.video_file), indent=4, sort_keys=True)
            json_str_lines = json_str.splitlines()
            self.video_info_json_start_row = len(self.display_lines)
            self.display_lines.extend(json_str_lines)
            self.video_info_json_end_row = len(self.display_lines)

        return self.display_lines

def edit_individual_video_file(video_file: imdb_utils.VideoFile, auto_search: bool = False, additional_commands: List[str] = None,  dialog_msg_suffix: str = ''):
    video_file_edit = VideoFileEdit(video_file, additional_commands)

    if auto_search:
        if video_file.scrubbed_file_year:
            video_file_edit.do_search_and_load_detail(video_file.scrubbed_file_name, video_file.scrubbed_file_year, dialog_msg_suffix=dialog_msg_suffix)
        else:
            video_file_edit.do_search_and_load_detail(video_file.scrubbed_file_name, dialog_msg_suffix=dialog_msg_suffix)

    with curses_gui.ScrollingPanel(rows=[''], height=0.75, width=0.75) as video_panel:
        while True:
            panel_width, panel_height = video_panel.get_width_height()
            display_lines = video_file_edit.setup_display_lines(panel_width, panel_height)

            video_panel.set_rows(display_lines)
            # if video_panel_hilited_row:
            #     video_panel.set_hilighted_row(video_panel_hilited_row)
            #     video_panel_hilited_row = None
            video_panel.show()

            run_result = video_panel.run()

            if run_result.key == curses_gui.Keycodes.ESCAPE:
                raise UserCancelException()

            if run_result.row_index == 0:
                try:
                    video_file_edit.do_search_and_load_detail(video_file.scrubbed_file_name, video_file.scrubbed_file_year, dialog_msg_suffix=dialog_msg_suffix)
                except UserCancelException:
                    logging.info('User cancelled IMDB search/detail fetch')

            elif run_result.row_index == 1:
                try:
                    video_file_edit.do_search_and_load_detail(video_file.scrubbed_file_name, video_file.scrubbed_file_year, ask_for_name=True, dialog_msg_suffix=dialog_msg_suffix)
                except UserCancelException:
                    logging.info('User cancelled IMDB search/detail fetch')

            elif video_file_edit.imdb_search_results and video_file_edit.imdb_search_results_start_row <= run_result.row_index < video_file_edit.imdb_search_results_end_row:
                try:
                    imdb_selected_detail_index = run_result.row_index - video_file_edit.imdb_search_results_start_row
                    video_file_edit.load_imdb_detail_info(imdb_selected_detail_index, dialog_msg_suffix)
                    video_file_edit.imdb_selected_detail_index = imdb_selected_detail_index
                except UserCancelException:
                    logging.info('User cancelled IMDB search/detail fetch')

#             elif additional_commands and additional_command_start_row <= run_result.row_index < additional_command_end_row:
#                 return additional_commands[run_result.row_index - 2]
#
#             elif imdb_search_results and imdb_search_results_start_row <= run_result.row_index < imdb_search_results_end_row:
#                 imdb_selected_detail_index = run_result.row_index - imdb_search_results_start_row
#
#             # elif run_result.row_index >= imdb_detail_start_row:
#             #     if (imdb_selected_detail_index == run_result.row_index - imdb_detail_start_row) and (imdb_detail_result := imdb_detail_results[imdb_selected_detail_index]):
#             #         video_file.imdb_tt = imdb_detail_result.imdb_tt
#             #         video_file.imdb_rating = imdb_detail_result.imdb_rating
#             #         video_file.imdb_name = imdb_detail_result.imdb_name
#             #         video_file.imdb_year = imdb_detail_result.imdb_year
#             #         video_file.imdb_genres = imdb_detail_result.imdb_genres
#             #         video_file.imdb_plot = imdb_detail_result.imdb_plot
#             #         video_file.is_dirty = True
#             #         return video_file
#             #
#             #     imdb_selected_detail_index = run_result.row_index - imdb_detail_start_row
#             #
#             #     if imdb_detail_results[imdb_selected_detail_index] is None:
#             #         try:
#             #             imdb_info = imdb_search_results[imdb_selected_detail_index]
#             #             if imdb_detail_result := get_imdb_detail_info(imdb_info):
#             #                 imdb_detail_results[imdb_selected_detail_index] = imdb_detail_result
#             #         except UserCancelException:
#             #             logging.info('User cancelled IMDB search/detail fetch')
#             #         finally:
#             #             continue

# def edit_individual_video_file(video_file: imdb_utils.VideoFile, auto_search: bool = False, additional_commands: List[str] = None,  dialog_msg_suffix: str = ''):
#     imdb_search_results = []
#     imdb_detail_results = []
#     imdb_selected_detail_index = None
#     video_panel_hilited_row = None
#
#     if auto_search:
#         if imdb_search_results := get_imdb_search_info(video_file.scrubbed_file_name, video_file.scrubbed_file_year, dialog_msg_suffix):
#             imdb_detail_results : List[Optional[imdb_utils.IMDBInfo]] = [None] * len(imdb_search_results)
#             if imdb_detail_result := get_imdb_detail_info(imdb_search_results[0], dialog_msg_suffix):
#                 imdb_detail_results[0] = imdb_detail_result
#                 imdb_selected_detail_index = 0
#         else:
#             with curses_gui.DialogBox(prompt=[f'No search results for "{video_file.scrubbed_file_name}"'], buttons_text=['OK']) as dialog_box:
#                 dialog_box.run()
#
#     with curses_gui.ScrollingPanel(rows=[''], height=0.75, width=0.75) as video_panel:
#         while True:
#             additional_command_start_row = -1
#             additional_command_end_row = -1
#             imdb_search_results_start_row = -1
#             imdb_search_results_end_row = -1
#             imdb_detail_start_row = -1
#             imdb_detail_end_row = -1
#             video_info_json_start_row = -1
#             video_info_json_end_row = -1
#
#             display_lines = list()
#             if video_file.scrubbed_file_year:
#                 display_lines.append(f'Search IMDB for "{video_file.scrubbed_file_name} ({video_file.scrubbed_file_year})"')
#             else:
#                 display_lines.append(f'Search IMDB for "{video_file.scrubbed_file_name}"')
#             display_lines.append(f'Search IMDB for other target')
#
#             if additional_commands:
#                 additional_command_start_row = len(display_lines)
#                 display_lines.extend(additional_commands)
#                 additional_command_end_row = len(display_lines)
#
#             display_lines.append(curses_gui.HorizontalLine())
#
#             if imdb_search_results:
#                 max_name_length = 0
#                 max_tt_length = 0
#                 for i in range(len(imdb_search_results)):
#                     imdb_info = imdb_detail_results[i] or imdb_search_results[i]
#                     max_name_length = max(max_name_length, len(imdb_info.imdb_name))
#                     max_tt_length = max(max_tt_length, len(imdb_info.imdb_tt))
#                 max_name_length = min(max_name_length, 75)
#
#                 imdb_search_results_start_row = len(display_lines)
#                 for i in range(len(imdb_search_results)):
#                     imdb_info = imdb_detail_results[i] or imdb_search_results[i]
#                     if i == imdb_selected_detail_index:
#                         imdb_info_str = f'=> {imdb_info.imdb_tt:{max_tt_length}} {imdb_info.imdb_name[:max_name_length]: <{max_name_length}}  [{imdb_info.imdb_year[:4]: <4}] [{imdb_info.imdb_rating: <3}] {imdb_info.imdb_plot}'
#                     else:
#                         imdb_info_str = f'   {imdb_info.imdb_tt:{max_tt_length}} {imdb_info.imdb_name[:max_name_length]: <{max_name_length}}  [{imdb_info.imdb_year[:4]: <4}] [{imdb_info.imdb_rating: <3}] {imdb_info.imdb_plot}'
#                     display_lines.append(imdb_info_str)
#                 imdb_search_results_end_row = len(display_lines)
#                 display_lines.append(curses_gui.HorizontalLine())
#
#             if imdb_selected_detail_index is not None and imdb_detail_results and imdb_detail_results[imdb_selected_detail_index]:
#                 pass
#             else:
#                 json_str = json.dumps(dataclasses.asdict(video_file), indent=4, sort_keys=True)
#                 json_str_lines = json_str.splitlines()
#                 video_info_json_start_row = len(display_lines)
#                 display_lines.extend(json_str_lines)
#                 video_info_json_end_row = len(display_lines)
#
#             # panel_width, panel_height = video_panel.get_width_height()
#             # imdb_detail_start_row = len(display_lines_header)
#             # display_lines_body = setup_video_file_edit_body(video_file, imdb_detail_results, imdb_selected_detail_index, panel_width)
#             # display_lines = display_lines_header + display_lines_body
#
#             video_panel.set_rows(display_lines)
#             if video_panel_hilited_row:
#                 video_panel.set_hilighted_row(video_panel_hilited_row)
#                 video_panel_hilited_row = None
#             video_panel.show()
#
#             run_result = video_panel.run()
#
#             if run_result.key == curses_gui.Keycodes.ESCAPE:
#                 raise UserCancelException()
#
#             if run_result.row_index == 0 or run_result.row_index == 1:
#                 search_file_name = video_file.scrubbed_file_name
#                 search_file_year = video_file.scrubbed_file_year
#
#                 if run_result.row_index == 1:
#                     with curses_gui.InputPanel(prompt='Enter IMDB search target: ', default_value=video_file.scrubbed_file_name) as input_panel:
#                         search_file_name = input_panel.run()
#                     if search_file_name is None:
#                         continue
#
#                 try:
#                     imdb_detail_results = []
#                     imdb_search_results = get_imdb_search_info(search_file_name, search_file_year, dialog_msg_suffix)
#                     if imdb_search_results:
#                         imdb_detail_results : List[Optional[imdb_utils.IMDBInfo]] = [None] * len(imdb_search_results)
#                         imdb_detail_result = get_imdb_detail_info(imdb_search_results[0], dialog_msg_suffix)
#                         if imdb_detail_result:
#                             imdb_detail_results[0] = imdb_detail_result
#                         else:
#                             with curses_gui.DialogBox(prompt=[f'No search results for "{video_file.scrubbed_file_name}"'], buttons_text=['OK']) as dialog_box:
#                                 dialog_box.run()
#                     else:
#                         video_panel_hilited_row = imdb_detail_start_row
#                         imdb_selected_detail_index = 0
#                 except UserCancelException:
#                     logging.info('User cancelled IMDB search/detail fetch')
#
#             elif additional_commands and additional_command_start_row <= run_result.row_index < additional_command_end_row:
#                 return additional_commands[run_result.row_index - 2]
#
#             elif imdb_search_results and imdb_search_results_start_row <= run_result.row_index < imdb_search_results_end_row:
#                 imdb_selected_detail_index = run_result.row_index - imdb_search_results_start_row
#
#             # elif run_result.row_index >= imdb_detail_start_row:
#             #     if (imdb_selected_detail_index == run_result.row_index - imdb_detail_start_row) and (imdb_detail_result := imdb_detail_results[imdb_selected_detail_index]):
#             #         video_file.imdb_tt = imdb_detail_result.imdb_tt
#             #         video_file.imdb_rating = imdb_detail_result.imdb_rating
#             #         video_file.imdb_name = imdb_detail_result.imdb_name
#             #         video_file.imdb_year = imdb_detail_result.imdb_year
#             #         video_file.imdb_genres = imdb_detail_result.imdb_genres
#             #         video_file.imdb_plot = imdb_detail_result.imdb_plot
#             #         video_file.is_dirty = True
#             #         return video_file
#             #
#             #     imdb_selected_detail_index = run_result.row_index - imdb_detail_start_row
#             #
#             #     if imdb_detail_results[imdb_selected_detail_index] is None:
#             #         try:
#             #             imdb_info = imdb_search_results[imdb_selected_detail_index]
#             #             if imdb_detail_result := get_imdb_detail_info(imdb_info):
#             #                 imdb_detail_results[imdb_selected_detail_index] = imdb_detail_result
#             #         except UserCancelException:
#             #             logging.info('User cancelled IMDB search/detail fetch')
#             #         finally:
#             #             continue
#

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
                    except UserCancelException:
                        logging.info('User cancelled video file edit')

    def update_all_video_file_data(self):
        if not self.video_files:
            with curses_gui.DialogBox(prompt=['No video files to process'], buttons_text=['OK']) as dialog_box:
                dialog_box.run()
            return

        num_video_files = len(self.video_files)
        num_video_files_processed = 0

        for i, video_file in enumerate(self.video_files):
            if video_file.imdb_tt:
                continue

            additional_commands = []
            if i < num_video_files - 1:
                for j in range(i + 1, num_video_files):
                    if not self.video_files[j].imdb_tt:
                        additional_commands.append(f'Skip to next video file ("{self.video_files[j].scrubbed_file_name}" [{j}/{num_video_files}])')
                        break
            additional_commands.append('Stop Updating')

            try:
                dialog_msg_suffix = f' [{i}/{num_video_files}]...'
                result = edit_individual_video_file(video_file, auto_search=True, additional_commands=additional_commands, dialog_msg_suffix=dialog_msg_suffix)
                if video_file.is_dirty:
                    self.video_files_is_dirty = True
                if result == 'Stop Updating':
                    break
                num_video_files_processed += 1
            except UserCancelException:
                logging.info('User cancelled video file edit')

                with curses_gui.DialogBox(prompt=['Continue processing or Cancel?'], buttons_text=['Continue', 'Cancel']) as dialog_box:
                    if dialog_box.run() == 'Cancel':
                        break

        with curses_gui.DialogBox(prompt=[f'Processed {num_video_files_processed} video files']) as dialog_box:
            dialog_box.run()

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


# For Pycharm "Attach to Process" execute: sudo sysctl kernel.yama.ptrace_scope=0

if __name__ == '__main__':
    logging.basicConfig(filename='/tmp/imdb_scraper.log', format='[%(process)d]:%(levelname)s:%(funcName)s:%(lineno)d: %(message)s', level=logging.INFO)

    logging.info('Starting up...')
    curses_gui.console_gui_main(MyMenu)
    logging.info('Ending.')
