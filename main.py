#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import dataclasses
import datetime
import functools
import logging
import os
import json
import math
import selectors
import sys
import threading
import time
import traceback
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
        self.menu_choices.append(('Update Video Info', self.update_all_video_file_data))
        self.menu_choices.append((curses_gui.HorizontalLine(), None))
        self.menu_choices.append(('test_scrolling_panel_grid_mode', self.test_scrolling_panel))
        self.menu_choices.append(('test_scrolling_panel_select_grid_cells', self.test_scrolling_panel_select_grid_cells))
        self.menu_choices.append(('test_scrolling_panel_100_rows', self.test_scrolling_panel_100_rows))
        self.menu_choices.append(('test_scrolling_panel_width', self.test_scrolling_panel_width))
        self.menu_choices.append(('test_scrolling_panel_width_height', self.test_scrolling_panel_width_height))

    def quit_confirm(self):
        if self.video_files_is_dirty:
            with curses_gui.MessagePanel(['Video data has been updated but not saved']) as message_panel:
                message_panel.run()
            return False
        else:
            return True

    @staticmethod
    def test_scrolling_panel_width_height():
        header_columns = list()
        header_columns.append(curses_gui.Column('Header Column 1', colour=curses_gui.CursesColourBinding.COLOUR_CYAN_BLACK))
        header_columns.append(curses_gui.Column('Header Column 2', colour=curses_gui.CursesColourBinding.COLOUR_CYAN_BLACK))
        header_row = curses_gui.Row(header_columns)

        display_lines = [curses_gui.Row(['1', 'One']),
                         curses_gui.Row(['2', 'Twwwwwwwwwwwwwwwoooo']),
                         curses_gui.Row(['333333333333', 'Three']),
                         curses_gui.Row(['4', 'Four']),
                         curses_gui.HorizontalLine(),
                         curses_gui.Row(['555', 'Five']), ]
        with curses_gui.ScrollingPanel(rows=display_lines, header_row=header_row, width=0.5, height=0.5, inner_padding=True) as scrolling_panel:
            scrolling_panel.run()

    @staticmethod
    def test_scrolling_panel_width():
        header_columns = list()
        header_columns.append(curses_gui.Column('Header Column 1', colour=curses_gui.CursesColourBinding.COLOUR_CYAN_BLACK))
        header_columns.append(curses_gui.Column('Header Column 2', colour=curses_gui.CursesColourBinding.COLOUR_CYAN_BLACK))
        header_row = curses_gui.Row(header_columns)

        display_lines = [curses_gui.Row(['1', 'One']),
                         curses_gui.Row(['2', 'Twwwwwwwwwwwwwwwoooo']),
                         curses_gui.Row(['333333333333', 'Three']),
                         curses_gui.Row(['4', 'Four']),
                         curses_gui.HorizontalLine(),
                         curses_gui.Row(['555', 'Five']), ]
        with curses_gui.ScrollingPanel(rows=display_lines, header_row=header_row, width=25, height=20, inner_padding=True) as scrolling_panel:
            scrolling_panel.run()

    @staticmethod
    def test_scrolling_panel():
        display_lines = [curses_gui.Row(['1', 'One']),
                         curses_gui.Row(['2', 'Twwwwwwwwwwwwwwwoooo']),
                         curses_gui.Row(['333333333333', 'Three']),
                         curses_gui.Row(['4', 'Four']),
                         curses_gui.HorizontalLine(),
                         curses_gui.Row(['555', 'Five']), ]
        with curses_gui.ScrollingPanel(rows=display_lines, inner_padding=True) as scrolling_panel:
            scrolling_panel.run()

    @staticmethod
    def test_scrolling_panel_select_grid_cells():
        display_lines = [curses_gui.Row(['1', 'One']),
                         curses_gui.Row(['2', 'Twwwwwwwwwwwwwwwoooo']),
                         curses_gui.Row(['333333333333', 'Three']),
                         curses_gui.Row(['4', 'Four']),
                         curses_gui.HorizontalLine(),
                         curses_gui.Row(['555', 'Five']), ]
        with curses_gui.ScrollingPanel(rows=display_lines, inner_padding=True, select_grid_cells=True) as scrolling_panel:
            scrolling_panel.run()

    @staticmethod
    def test_scrolling_panel_100_rows():
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
        header_columns.append(curses_gui.Column('Header Column 1', colour=curses_gui.CursesColourBinding.COLOUR_CYAN_BLACK))
        header_columns.append(curses_gui.Column('Header Column 2', colour=curses_gui.CursesColourBinding.COLOUR_CYAN_BLACK))
        header_row = curses_gui.Row(header_columns)
        with curses_gui.ScrollingPanel(rows=display_lines, inner_padding=True, header_row=header_row) as scrolling_panel:
            scrolling_panel.run()

    # @staticmethod
    # def test_thread_dialog():
    #     class MyThread(threading.Thread):
    #         def __init__(self):
    #             super().__init__(daemon=True)
    #             self.keep_going = True
    #             self.imdb_search_response = None
    #
    #         def run(self) -> None:
    #             logging.info('Fetching IMDB info...')
    #             self.imdb_search_response = imdb_utils.get_imdb_search_results('21 jump street')
    #             logging.info('Fetched IMDB info')
    #
    #             logging.info('MyThread exit.')
    #
    #     logging.info('Creating DialogBox')
    #     time_str = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S.%f")
    #     with curses_gui.DialogBox(prompt=[time_str], buttons_text=['OK', 'Cancel']) as dialog_box:
    #         logging.info('Creating MyThread')
    #         my_thread = MyThread()
    #         logging.info('Starting MyThread')
    #         my_thread.start()
    #
    #         while True:
    #             logging.info('Calling DialogBox.run')
    #             result = dialog_box.run(key_timeout_msec=100)
    #             logging.info('DialogBox result = %s', result)
    #             if result == -1:
    #                 logging.info('User pressed Keycodes.ESCAPE')
    #                 break
    #             else:
    #                 time_str = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S.%f")
    #                 dialog_box.set_prompt(time_str)
    #
    #             if my_thread.imdb_search_response:
    #                 logging.info('MyThread got the IMDB data')
    #                 break
    #
    #         logging.info('Stopping MyThread')
    #         my_thread.keep_going = False
    #
    #         imdb_info_list = imdb_utils.parse_imdb_search_results(my_thread.imdb_search_response)
    #
    #         header_columns = [curses_gui.Column('IMDB REFNUM', colour=curses_gui.CursesColourBinding.COLOUR_BLACK_RED),
    #                           curses_gui.Column('IMDB NAME', colour=curses_gui.CursesColourBinding.COLOUR_BLACK_RED),
    #                           curses_gui.Column('IMDB YEAR', colour=curses_gui.CursesColourBinding.COLOUR_BLACK_RED)]
    #         header_row = curses_gui.Row(header_columns)
    #         display_lines = [curses_gui.Row([imdb_info.imdb_tt, imdb_info.imdb_name, imdb_info.imdb_year]) for imdb_info in imdb_info_list]
    #         with curses_gui.ScrollingPanel(rows=display_lines, header_row=header_row, inner_padding=True) as imdb_search_results_panel:
    #             while True:
    #                 run_result = imdb_search_results_panel.run()
    #                 if run_result.key == curses_gui.Keycodes.ESCAPE:
    #                     break

    # @staticmethod
    # def test_selectable_thread_dialog():
    #     class SelectableThread(threading.Thread):
    #         def __init__(self):
    #             super().__init__(daemon=True)
    #             self.imdb_search_response = None
    #             self.read_pipe_fd, self.write_pipe_fd = os.pipe()
    #             self.read_buffer = ''
    #
    #         def process_pipe_read(self):
    #             text = os.read(my_thread.read_pipe_fd, 1024)
    #             if text:
    #                 self.read_buffer += text.decode('ascii')
    #
    #         def get_message(self):
    #             read_message = None
    #             newline_i = self.read_buffer.find('\n')
    #             if newline_i >= 0:
    #                 read_message = self.read_buffer[:newline_i]
    #                 self.read_buffer = self.read_buffer[newline_i + 1:]
    #             return read_message
    #
    #         def run(self) -> None:
    #             for i in range(10):
    #                 os.write(self.write_pipe_fd, bytes(f'SelectableThread pass {i}\n', 'ascii'))
    #                 time.sleep(1.0)
    #
    #             logging.info('SelectableThread closing self.write_pipe_fd')
    #             os.close(self.write_pipe_fd)
    #
    #             logging.info('SelectableThread exit.')
    #
    #     logging.info('Creating DialogBox')
    #     time_str = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S.%f")
    #     with curses_gui.DialogBox(prompt=[time_str], buttons_text=['OK', 'Cancel']) as dialog_box:
    #         dialog_box.show()
    #
    #         logging.info('Creating SelectableThread')
    #         my_thread = SelectableThread()
    #         logging.info('Starting SelectableThread')
    #         my_thread.start()
    #
    #         sel = selectors.DefaultSelector()
    #         sel.register(my_thread.read_pipe_fd, selectors.EVENT_READ, 'PIPE')
    #
    #         while my_thread.is_alive():
    #             time_str = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S.%f")
    #             dialog_box.set_prompt(time_str, refresh=True)
    #
    #             # events = sel.select(0.5)
    #             events = sel.select()
    #
    #             if not events:
    #                 continue
    #
    #             for selector_key, event_mask in events:
    #                 if selector_key.data == 'PIPE':
    #                     my_thread.process_pipe_read()
    #                     while True:
    #                         message = my_thread.get_message()
    #                         if not message:
    #                             break
    #                         logging.info(f'Got message from worker thread: {message}')
    #
    #         sel.unregister(my_thread.read_pipe_fd)
    #         sel.close()

    # @staticmethod
    # def test_threaded_dialog():
    #     def my_task():
    #         for i in range(10):
    #             logging.info('Sleeping...')
    #             time.sleep(1.0)
    #         return 'Work Complete'
    #
    #     logging.info('Creating SelectableThread')
    #     my_thread = curses_gui.SelectableThread(my_task)
    #     logging.info('Starting SelectableThread')
    #     my_thread.start()
    #
    #     sel = selectors.DefaultSelector()
    #     sel.register(my_thread.read_pipe_fd, selectors.EVENT_READ, 'PIPE')
    #     sel.register(sys.stdin, selectors.EVENT_READ, 'STDIN')
    #
    #     threaded_dialog_result = curses_gui.ThreadedDialogResult(selectable_thread=my_thread)
    #
    #     logging.info('Creating DialogBox')
    #     with curses_gui.DialogBox(prompt=[datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S.%f")], buttons_text=['OK', 'Cancel'], show_immediately=True) as dialog_box:
    #         keep_going = True
    #
    #         while keep_going:
    #             # The timeout on sel.select() is 0.5s, so we will update the dialog prompt as we wait
    #             dialog_box.set_prompt(datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S.%f"), refresh=True)
    #
    #             if not my_thread.is_alive():
    #                 keep_going = False
    #             elif events := sel.select(0.5):
    #                 for selector_key, event_mask in events:
    #                     if selector_key.data == 'PIPE':
    #                         logging.info(f'Got result from worker thread: {my_thread.callable_result}')
    #                     elif selector_key.data == 'STDIN':
    #                         logging.info(f'Ready to read sys.stdin')
    #                         dialog_box_result = dialog_box.run(single_key=True)
    #                         logging.info(f'Got {dialog_box_result=}')
    #                         if dialog_box_result == 'Cancel':
    #                             keep_going = False
    #                             threaded_dialog_result.dialog_result = dialog_box_result
    #
    #         sel.unregister(my_thread.read_pipe_fd)
    #         sel.unregister(sys.stdin)
    #         sel.close()
    #
    #     # TODO: Clear stdin for stacked keypresses?
    #
    #     return threaded_dialog_result

    # @staticmethod
    # def test_cancellable_threaded_dialog():
    #     def my_task():
    #         for i in range(10):
    #             logging.info('Sleeping...')
    #             time.sleep(1.0)
    #         return 'Work Complete'
    #
    #     threaded_dialog_result = curses_gui.run_cancellable_thread_dialog(my_task, 'Waiting for background task to complete...')
    #
    #     logging.info(f'Got final threaded_dialog_result: dialog_result={threaded_dialog_result.dialog_result}, callable_result={threaded_dialog_result.selectable_thread.callable_result}')
    @staticmethod
    def show_exception_details(exc_type, exc_value, exc_traceback):
        message_lines = [f'Caught an exception: {exc_value}']
        exception_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        for exception_line in exception_lines:
            for line in exception_line.split('\n'):
                if line.strip():
                    message_lines.append(line)

        for l in message_lines:
            logging.error(l)

        with curses_gui.MessagePanel(message_lines) as message_panel:
            message_panel.run()
            return

    # def update_video_imdb_info(self, video_file: imdb_utils.VideoFile):
    #     imdb_details_task = functools.partial(imdb_utils.get_parse_imdb_tt_info, video_file.imdb_tt)
    #     threaded_dialog_result = curses_gui.run_cancellable_thread_dialog(imdb_details_task, 'Fetching IMDB Detail Info...')
    #     if threaded_dialog_result.dialog_result is not None:
    #         return
    #
    #     if threaded_dialog_result.selectable_thread.callable_exception_info_tuple:
    #         exc_type, exc_value, exc_traceback = threaded_dialog_result.selectable_thread.callable_exception_info_tuple
    #         self.show_exception_details(exc_type, exc_value, exc_traceback)
    #         return
    #
    #     detail_imdb_info: imdb_utils.IMDBInfo = threaded_dialog_result.selectable_thread.callable_result
    #
    #     video_file.imdb_tt = detail_imdb_info.imdb_tt
    #     video_file.imdb_rating = detail_imdb_info.imdb_rating
    #     video_file.imdb_name = detail_imdb_info.imdb_name
    #     video_file.imdb_year = detail_imdb_info.imdb_year
    #     video_file.imdb_genres = detail_imdb_info.imdb_genres
    #     video_file.imdb_plot = detail_imdb_info.imdb_plot
    #
    #     self.video_files_is_dirty = True

    # def search_video_imdb_info(self, video_file: imdb_utils.VideoFile):
    #     file_name = video_file.scrubbed_file_name
    #     file_year = video_file.scrubbed_file_year
    #     imdb_search_task = functools.partial(imdb_utils.get_parse_imdb_search_results, file_name, file_year)
    #     threaded_dialog_result = curses_gui.run_cancellable_thread_dialog(imdb_search_task, 'Fetching IMDB Search Info...')
    #     if threaded_dialog_result.dialog_result is not None:
    #         return
    #
    #     if threaded_dialog_result.selectable_thread.callable_exception_info_tuple:
    #         exc_type, exc_value, exc_traceback = threaded_dialog_result.selectable_thread.callable_exception_info_tuple
    #         self.show_exception_details(exc_type, exc_value, exc_traceback)
    #         return
    #
    #     search_imdb_info_list: List[imdb_utils.IMDBInfo] = threaded_dialog_result.selectable_thread.callable_result
    #
    #     header_columns = [curses_gui.Column('*', colour=curses_gui.CursesColourBinding.COLOUR_CYAN_BLACK),
    #                       curses_gui.Column('REFNUM', colour=curses_gui.CursesColourBinding.COLOUR_CYAN_BLACK),
    #                       curses_gui.Column('NAME', colour=curses_gui.CursesColourBinding.COLOUR_CYAN_BLACK),
    #                       curses_gui.Column('YEAR', colour=curses_gui.CursesColourBinding.COLOUR_CYAN_BLACK)]
    #     header_row = curses_gui.Row(header_columns)
    #     display_rows = [curses_gui.Row(['', imdb_info.imdb_tt, imdb_info.imdb_name, imdb_info.imdb_year]) for imdb_info in search_imdb_info_list]
    #     with curses_gui.ScrollingPanel(rows=display_rows, header_row=header_row, inner_padding=True) as imdb_search_results_panel:
    #         while True:
    #             run_result = imdb_search_results_panel.run()
    #             if run_result.key == curses_gui.Keycodes.ESCAPE:
    #                 return None
    #             elif run_result.key == curses_gui.Keycodes.RETURN:
    #                 return search_imdb_info_list[run_result.row_index]

    def get_imdb_detail_info(self, imdb_tt: str) -> Optional[imdb_utils.IMDBInfo]:
        imdb_details_task = functools.partial(imdb_utils.get_parse_imdb_tt_info, imdb_tt)
        threaded_dialog_result = curses_gui.run_cancellable_thread_dialog(imdb_details_task, 'Fetching IMDB Detail Info...')
        if threaded_dialog_result.dialog_result is not None:
            return None

        if threaded_dialog_result.selectable_thread.callable_exception_info_tuple:
            exc_type, exc_value, exc_traceback = threaded_dialog_result.selectable_thread.callable_exception_info_tuple
            self.show_exception_details(exc_type, exc_value, exc_traceback)
            return None

        detail_imdb_info: imdb_utils.IMDBInfo = threaded_dialog_result.selectable_thread.callable_result

        return detail_imdb_info


    def get_imdb_search_info(self, video_file: imdb_utils.VideoFile) -> Optional[List[imdb_utils.IMDBInfo]]:
        file_name = video_file.scrubbed_file_name
        file_year = video_file.scrubbed_file_year
        imdb_search_task = functools.partial(imdb_utils.get_parse_imdb_search_results, file_name, file_year)
        threaded_dialog_result = curses_gui.run_cancellable_thread_dialog(imdb_search_task, f'Fetching IMDB Search Info for "{file_name}"...')
        if threaded_dialog_result.dialog_result is not None:
            return None

        if threaded_dialog_result.selectable_thread.callable_exception_info_tuple:
            exc_type, exc_value, exc_traceback = threaded_dialog_result.selectable_thread.callable_exception_info_tuple
            self.show_exception_details(exc_type, exc_value, exc_traceback)
            return None

        search_imdb_info_list: List[imdb_utils.IMDBInfo] = threaded_dialog_result.selectable_thread.callable_result

        return search_imdb_info_list

    def display_individual_video_file(self, video_file: imdb_utils.VideoFile, auto_search = False):
        imdb_detail_row_offset = 3

        if auto_search:
            imdb_search_results = self.get_imdb_search_info(video_file) or []  # type: List[imdb_utils.IMDBInfo]
            imdb_detail_results = [None] * len(imdb_search_results) # type: List[Optional[imdb_utils.IMDBInfo]]
        else:
            imdb_search_results = []  # type: List[imdb_utils.IMDBInfo]
            imdb_detail_results = []  # type: List[Optional[imdb_utils.IMDBInfo]]

        with curses_gui.ScrollingPanel(rows=[''], height=0.75, width=0.75) as video_info_panel:
            while True:
                display_lines = ['Search IMDB', 'Clear IMDB Info', curses_gui.HorizontalLine()]

                if imdb_search_results:
                    max_name_length = 0
                    max_tt_length = 0
                    for i in range(len(imdb_search_results)):
                        imdb_info = imdb_detail_results[i] or imdb_search_results[i]
                        max_name_length = max(max_name_length, len(imdb_info.imdb_name))
                        max_tt_length = max(max_tt_length, len(imdb_info.imdb_tt))

                    for i in range(len(imdb_search_results)):
                        imdb_info = imdb_detail_results[i] or imdb_search_results[i]
                        imdb_info_str = f'{imdb_info.imdb_tt:{max_tt_length}} {imdb_info.imdb_name: <{max_name_length}}  [{imdb_info.imdb_year[:4]: <4}] [{imdb_info.imdb_rating: <3}] {imdb_info.imdb_plot}'
                        display_lines.append(imdb_info_str)
                    display_lines.append(curses_gui.HorizontalLine())

                json_str = json.dumps(dataclasses.asdict(video_file), indent=4, sort_keys=True)
                json_str_lines = json_str.splitlines()

                display_lines.extend(json_str_lines)
                video_info_panel.set_rows(display_lines)
                video_info_panel.show()

                run_result = video_info_panel.run()
                if run_result.key == curses_gui.Keycodes.ESCAPE:
                    break
                elif run_result.key == curses_gui.Keycodes.RETURN and run_result.row_index == 0:
                    imdb_search_results = self.get_imdb_search_info(video_file)
                    imdb_detail_results = [None] * len(imdb_search_results)

                elif run_result.key == curses_gui.Keycodes.RETURN and run_result.row_index == 1:
                    video_file.imdb_tt = ''
                    video_file.imdb_rating = ''
                    video_file.imdb_name = ''
                    video_file.imdb_year = ''
                    video_file.imdb_genres = []
                    video_file.imdb_plot = ''
                    self.video_files_is_dirty = True

                elif run_result.key == curses_gui.Keycodes.RETURN and imdb_search_results and imdb_detail_row_offset <= run_result.row_index < len(imdb_search_results) + imdb_detail_row_offset:
                    if imdb_detail_results[run_result.row_index - imdb_detail_row_offset] is None:
                        imdb_search_result = imdb_search_results[run_result.row_index - imdb_detail_row_offset]
                        imdb_detail_result = self.get_imdb_detail_info(imdb_search_result.imdb_tt)
                        if imdb_detail_result:
                            imdb_detail_results[run_result.row_index - imdb_detail_row_offset] = imdb_detail_result

                    if imdb_detail_results[run_result.row_index - imdb_detail_row_offset]:
                        detail_imdb_info = imdb_detail_results[run_result.row_index - imdb_detail_row_offset]
                        video_file.imdb_tt = detail_imdb_info.imdb_tt
                        video_file.imdb_rating = detail_imdb_info.imdb_rating
                        video_file.imdb_name = detail_imdb_info.imdb_name
                        video_file.imdb_year = detail_imdb_info.imdb_year
                        video_file.imdb_genres = detail_imdb_info.imdb_genres
                        video_file.imdb_plot = detail_imdb_info.imdb_plot
                        self.video_files_is_dirty = True

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
                display_rows = [curses_gui.Row([f'[{i:0{num_digits}d}]', video_file.scrubbed_file_name, str(video_file.scrubbed_file_year), f'[{video_file.imdb_tt}]', video_file.file_path]) for i, video_file in enumerate(self.video_files)]
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
            else:
                with curses_gui.DialogBox(prompt=[f'Search IMDB for "{video_file.scrubbed_file_name}"?'], buttons_text=['OK', 'Cancel']) as dialog_box:
                    if dialog_box.run() != 'OK':
                        break

                self.display_individual_video_file(video_file, True)

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
