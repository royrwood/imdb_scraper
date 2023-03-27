# Example usage:

# from imdb_scraper.curses_gui import LOGGER
# from imdb_scraper.curses_gui import MainMenu
# from imdb_scraper.curses_gui import console_gui_main
#
#
# class MyMenu(MainMenu):
#     def __init__(self):
#         super(MyMenu, self).__init__()
#
#     def set_menu_choices(self):
#         self.menu_choices = []
#         self.menu_choices.append(('Some menu choice', self.class_callback_function))
#         self.menu_choices.append(('Another menu choice', plain_function_callback))
#
#     def class_callback_function(self):
#         LOGGER.info('Callback for some menu choice (class method callback)')
#
# def plain_function_callback():
#     LOGGER.info('Callback for another menu choice (plain function callback)')
#
#
# if __name__ == '__main__':
#     console_gui_main(MyMenu)


import copy
import curses
import curses.panel
import dataclasses
import logging
import os
import selectors
import sys
import threading
import traceback
from enum import IntEnum, unique
from typing import List, Tuple, Callable, Union, Optional, Dict, Text


# Define some nicer constants for keystrokes
@unique
class Keycodes(IntEnum):
    ESCAPE = 27
    RETURN = 10
    BACKSPACE = 127
    DELETE = 330


# Define some constants for the curses colour bindings we set up
@unique
class CursesColourBinding(IntEnum):
    COLOUR_WHITE_BLACK = 0
    COLOUR_CYAN_BLACK = 1
    COLOUR_RED_BLACK = 2
    COLOUR_BLACK_WHITE = 3
    COLOUR_YELLOW_BLACK = 4
    COLOUR_BLACK_YELLOW = 5
    COLOUR_BLACK_RED = 6


class UserCancelException(Exception):
    pass

class AsyncThreadException(Exception):
    pass


class CursesStdscrType:
    """A bogus class used to define behaviour of CURSES_STDSCR so Pycharm linter will stop complaining!
    Actual type is weird: type(stdscr) = <type '_curses.curses window'>
    """
    def clear(self):
        pass

    def refresh(self):
        pass

    @staticmethod
    def getmaxyx() -> Tuple[int, int]:
        return 0, 0


CURSES_STDSCR: CursesStdscrType = CursesStdscrType()


class SelectableThread(threading.Thread):
    def __init__(self, callable_task):
        super().__init__(daemon=True)
        self.callable_task: Callable = callable_task
        self.callable_result = None
        self.callable_exception_info_tuple: Optional[Exception] = None
        self.read_pipe_fd, self.write_pipe_fd = os.pipe()

    def run(self) -> None:
        if self.callable_task:
            # noinspection PyBroadException
            try:
                self.callable_result = self.callable_task()
            except Exception:
                self.callable_exception_info_tuple = sys.exc_info()

                # exc_type, exc_value, exc_traceback = sys.exc_info()
                # logging.error(u'Caught an exception: %s', exc_value)
                # exception_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
                # for l in exception_lines:
                #     logging.error(l.strip())

        os.write(self.write_pipe_fd, b'\n')
        os.close(self.write_pipe_fd)


@dataclasses.dataclass
class ThreadedDialogResult:
    dialog_result: Optional[str] = None
    selectable_thread: SelectableThread = None


class Column:
    """An object to represent a column/field in a row in a ScrollingPanel.
       If the column width is not specified, it defaults to the length of the text.
    """
    def __init__(self, text: str = '', colour: CursesColourBinding = CursesColourBinding.COLOUR_WHITE_BLACK, width: Optional[int] = None):
        self.text = text
        self.text_length = len(text) if text else 0
        self.colour = colour
        self.width = width or self.text_length


class Row:
    """An object to represent a row in a ScrollingPanel.
       The Row may contain a list of string or Column objects

       Examples:
           Row(row_content='This is a simple line of text')
           Row(row_content=['Dog', 'Cow'])
           Row(row_content=[Column('Dog'), Column('Cow'), Column('Clarus', width=10)])
    """
    def __init__(self, row_content: Union[str, Column, List[str], List[Column]] = ''):
        if isinstance(row_content, Column):
            self.columns = [copy.deepcopy(row_content)]
        elif isinstance(row_content, str):
            self.columns = [Column(text=row_content)]
        elif isinstance(row_content, list):
            self.columns = list()
            for i, rc in enumerate(row_content):
                if isinstance(rc, Column):
                    self.columns.append(copy.deepcopy(rc))
                elif isinstance(rc, str):
                    self.columns.append(Column(text=rc))
                else:
                    self.columns.append(Column(text=str(rc)))
        else:
            self.columns = [Column(text=str(row_content))]


class HorizontalLine(Row):
    """A row of this type will be rendered as a horizontal line.
    """
    def __init__(self):
        super(HorizontalLine, self).__init__()


class ScrollPanelRunResult:
    """When a ScrollPanel exits (e.g. user presses return or escape), an object of this type is returned.
    """
    def __init__(self, row_index, col_index, text, key):
        self.row_index: int = row_index
        self.col_index: int = col_index
        self.text: str = text
        self.key: str = key


class ScrollingPanel:
    """This is the generic panel object that we use to display the user interface; you will probably subclass this and call the default run() method to handle keys and rendering
       Note that items are a list of str/unicode text or Row objects; the list can contain a mix of text and/or Row objects

       Simple example:
           my_panel = ScrollingPanel(items=['A simple str line of text', u'A unicode line of text'])

       An example with custom colour for a row:
           my_panel = ScrollingPanel(items=['A simple str line of text', u'A unicode line of text', Row('A row with custom colour', CursesColourBinding.COLOUR_RED_BLACK)])

       An example with multiple columns in a row:
           my_panel = ScrollingPanel(items=['A simple str line of text', u'A unicode line of text', Row(columns=[Column('Column 1'), Column('Column 2')]])

       An example with multiple columns and custom width and custom colour:
           my_panel = ScrollingPanel(items=['A simple str line of text', u'A unicode line of text', Row(columns=[Column('Column 1'), Column('Column 2', CursesColourBinding.COLOUR_RED_BLACK, 20)]])
    """
    def __init__(self, rows=None, top=None, left=None, width=None, height=None, draw_border=True, header_row: Union[str, Column, Row, List[str], List[Column]] = None, select_grid_cells=False, inner_padding=0, show_immediately=True, hilighted_row_index=None, hilighted_col_index=None, debug_name=None):
        self.draw_border = draw_border

        self.debug_name = debug_name

        self.select_grid_cells = select_grid_cells
        self.inner_padding = inner_padding

        self.window = None
        self.panel = None

        self.stdscr_height, self.stdscr_width = CURSES_STDSCR.getmaxyx()  # If/when we eventually handle dynamic screen sizing, this will need to be updated

        # Keep track of the initial top/left/width/height in case we need to reset geometry according to those values later (e.g. after a resize or change of content)
        self.initial_top = top
        self.initial_left = left
        self.initial_height = height  # height >= 1 is a height in rows; height < 0 is indented from fullscreen height; 0.0 < height < 1.0 is fraction of fullscreen height
        self.initial_width = width  # width >= 1 is a width in characters; width < 0 is indented from fullscreen width; 0.0 < width < 1.0 is fraction of fullscreen width

        self.needs_render = False
        self.rows = None
        self.num_rows = 0
        self.num_cols = 0
        self.rows_max_width = 0
        self.column_widths = None
        self.header_row = None
        self.num_header_rows = 0
        self.top_visible_row_index = 0
        self.hilighted_row_index = hilighted_row_index if hilighted_row_index is not None else 0
        self.hilighted_col_index = hilighted_col_index if hilighted_col_index is not None else 0
        self.height = 0
        self.width = 0
        self.top = 0
        self.left = 0
        self.content_top = 0
        self.content_left = 0
        self.content_right = 0
        self.content_height = 0
        self.content_width = 0
        self.message_lines = None

        self.is_visible = False

        self.set_header(header_row)
        self.set_rows(rows)

        if show_immediately:
            self.show()

    def __enter__(self):
        return self

    def __exit__(self, _type, _value, _traceback):
        self.hide()

    def get_width_height(self):
        return self.width, self.height

    def set_header(self, header_row):
        if type(header_row) is Row:
            self.header_row = copy.deepcopy(header_row)
            self.num_header_rows = 1
        elif header_row:
            self.header_row = Row(header_row)
            self.num_header_rows = 1
        else:
            self.header_row = None
            self.num_header_rows = 0

    def set_rows(self, new_rows, hilighted_row=None):
        rows = []

        self.column_widths = list()
        
        if self.header_row:
            for column in self.header_row.columns:
                self.column_widths.append(column.width)

        if new_rows:
            for new_row in new_rows:
                if isinstance(new_row, Row):
                    insert_row = copy.deepcopy(new_row)
                else:
                    insert_row = Row(new_row)

                rows.append(insert_row)

                for ci, column in enumerate(insert_row.columns):
                    if ci >= len(self.column_widths):
                        self.column_widths.append(column.width)
                    else:
                        self.column_widths[ci] = max(self.column_widths[ci], column.width)

            self.num_cols = len(self.column_widths)

        self.rows = rows
        self.num_rows = len(self.rows)
        self.num_cols = len(self.column_widths)
        self.rows_max_width = sum(self.column_widths) + self.inner_padding * (self.num_cols - 1)
        self.needs_render = True
        self.top_visible_row_index = 0

        if self.hilighted_row_index >= self.num_rows:
            self.hilighted_row_index = max(self.num_rows - 1, 0)

        self.hilighted_col_index = 0

        # Since the row contents have changed, we need to recalculate the window geometry
        self.set_geometry()

        if hilighted_row is not None:
            self.set_hilighted_row(hilighted_row)

    def set_hilighted_row(self, new_hilighted_row, top_visible_row_index=None):
        if self.hilighted_row_index != new_hilighted_row:
            self.needs_render = True

        self.hilighted_row_index = new_hilighted_row

        if self.hilighted_row_index >= self.num_rows:
            self.hilighted_row_index = max(self.num_rows - 1, 0)

        if top_visible_row_index:
            if self.top_visible_row_index != top_visible_row_index:
                self.needs_render = True

            self.top_visible_row_index = top_visible_row_index

    def set_geometry(self):
        orig_window_height = self.height
        orig_window_width = self.width
        orig_window_top = self.top
        orig_window_left = self.left

        self.needs_render = True

        top = self.initial_top
        left = self.initial_left
        height = self.initial_height
        width = self.initial_width

        if height is None:
            self.height = min(self.stdscr_height, self.num_rows + 2 + self.num_header_rows)
        elif isinstance(height, float):
            self.height = min(self.stdscr_height, int(self.stdscr_height * height))
            # LOGGER.info('debug_name=%s, self.height = %s', self.debug_name, self.height)
        elif height <= 0:
            self.height = self.stdscr_height + 2 * height  # Since height < 0, the "+ 2*height" is really subtracting from the stdscr_height!
        else:
            self.height = height

        if width is None:
            self.width = min(self.stdscr_width, self.rows_max_width + 4)  # Leave a blank space at the left/right, and also account for the border
        elif isinstance(width, float):
            self.width = min(self.stdscr_width, int(self.stdscr_width * width))
            # LOGGER.info('debug_name=%s, self.width = %s', self.debug_name, self.width)
        elif width <= 0:
            self.width = self.stdscr_width + 2 * width  # Since width < 0, the "+ 2*width" is really subtracting from the stdscr_width!
        else:
            self.width = width

        if top is None:
            self.top = int((self.stdscr_height - self.height) // 2)
        else:
            self.top = top

        if left is None:
            self.left = int((self.stdscr_width - self.width) // 2)
        else:
            self.left = left

        if self.window and (orig_window_height != self.height or orig_window_width != self.width or orig_window_top != self.top or orig_window_left != self.left):
            if self.panel:
                self.panel.hide()
                del self.panel
                self.panel = None

            del self.window
            self.window = None

        if not self.window:
            self.window = curses.newwin(self.height, self.width, self.top, self.left)
            self.window.keypad(True)

        if not self.panel:
            self.panel = curses.panel.new_panel(self.window)
            if self.is_visible:
                self.panel.show()

        self.content_top = 1 + self.num_header_rows  # Leave 1 row for the border and then a row for the header, if there is one
        self.content_left = 2  # Left/right are indented by a space, and there is a border
        self.content_right = self.width - 2  # Left/right are indented by a space, and there is a border
        self.content_height = self.height - 2 - self.num_header_rows  # Account for top/bottom border and header
        self.content_width = self.width - 4  # Account for left/right border and a space on the left/right

    def hide(self):
        if self.panel:
            self.panel.hide()
            curses.panel.update_panels()
            CURSES_STDSCR.refresh()
        self.is_visible = False

    def show(self):
        if self.panel:
            # self.set_geometry()
            self.render(force=True)
            self.panel.show()
            curses.panel.update_panels()
            CURSES_STDSCR.refresh()
            self.is_visible = True

    def render(self, force=False):
        if not (force or self.needs_render):
            return

        self.window.erase()

        if self.draw_border:
            self.window.border()

        if self.header_row:
            x = self.content_left
            for ci, column in enumerate(self.header_row.columns):
                raw_text = column.text
                padding = self.inner_padding if ci < self.num_cols else 0
                column_width = self.column_widths[ci] + padding
                text_colour = column.colour

                if x + column_width > self.content_right or ci == self.num_cols - 1:
                    column_width = self.content_right - x
                    raw_text = raw_text[:column_width]

                padded_text = f'{raw_text: <{column_width}}'
                self.window.addstr(1, x, padded_text, curses.color_pair(text_colour))
                x += column_width

                if x >= self.content_right:
                    break

        for ri in range(0, self.content_height):
            row_index = self.top_visible_row_index + ri
            y = self.content_top + ri
            x = self.content_left

            if row_index >= self.num_rows:
                text_colour = CursesColourBinding.COLOUR_WHITE_BLACK
                raw_text = ''
                padded_text = u'{raw_text: <{width}}'.format(raw_text=raw_text, width=self.content_width)
                self.window.addstr(y, x, padded_text, curses.color_pair(text_colour))
                continue

            row = self.rows[row_index]

            if isinstance(row, HorizontalLine):
                if row_index == self.hilighted_row_index:
                    text_colour = CursesColourBinding.COLOUR_BLACK_YELLOW
                else:
                    text_colour = row.columns[0].colour
                self.window.hline(y, x, curses.ACS_HLINE, self.content_width, curses.color_pair(text_colour))
                continue

            for ci, column in enumerate(row.columns):
                raw_text = column.text
                padding = self.inner_padding if ci < self.num_cols else 0
                column_width = self.column_widths[ci] + padding

                if row_index == self.hilighted_row_index and (not self.select_grid_cells or ci == self.hilighted_col_index):
                    text_colour = CursesColourBinding.COLOUR_BLACK_YELLOW
                else:
                    text_colour = column.colour

                if x + column_width > self.content_right or ci == self.num_cols - 1:
                    column_width = self.content_right - x
                    raw_text = raw_text[:column_width]

                padded_text = f'{raw_text: <{column_width}}'
                self.window.addstr(y, x, padded_text, curses.color_pair(text_colour))
                x += column_width

                if x >= self.content_right:
                    break

        self.needs_render = False

    def handle_keystroke(self, key):
        hilighted_row_index = self.hilighted_row_index
        hilighted_col_index = self.hilighted_col_index
        top_visible_row_index = self.top_visible_row_index

        if key == curses.KEY_UP:
            hilighted_row_index -= 1
        elif key == curses.KEY_DOWN:
            hilighted_row_index += 1
        elif key == curses.KEY_LEFT:
            hilighted_col_index -= 1
        elif key == curses.KEY_RIGHT:
            hilighted_col_index += 1
        elif key == curses.KEY_PPAGE:
            if hilighted_row_index > top_visible_row_index:
                hilighted_row_index = top_visible_row_index
            else:
                hilighted_row_index -= self.content_height
        elif key == curses.KEY_NPAGE:
            if hilighted_row_index < top_visible_row_index + self.content_height - 1:
                hilighted_row_index = top_visible_row_index + self.content_height - 1
            else:
                hilighted_row_index += self.content_height
        elif key == curses.KEY_HOME:
            hilighted_row_index = 0
            hilighted_col_index = 0
        elif key == curses.KEY_END:
            hilighted_row_index = self.num_rows - 1
            hilighted_col_index = 0

        if hilighted_row_index < 0:
            hilighted_row_index = 0
        elif hilighted_row_index >= self.num_rows:
            hilighted_row_index = self.num_rows - 1

        if hilighted_row_index < top_visible_row_index:
            top_visible_row_index = hilighted_row_index
        elif hilighted_row_index >= top_visible_row_index + self.content_height:
            top_visible_row_index = hilighted_row_index - self.content_height + 1

        if top_visible_row_index < 0:
            top_visible_row_index = 0
        elif top_visible_row_index >= self.num_rows:
            top_visible_row_index = self.num_rows - 1

        row = self.rows[hilighted_row_index]
        if self.hilighted_row_index != hilighted_row_index:
            if hilighted_col_index >= len(row.columns):
                hilighted_col_index = len(row.columns) - 1
        else:
            if hilighted_col_index < 0:
                hilighted_col_index = len(row.columns) - 1
            elif hilighted_col_index >= len(row.columns):
                hilighted_col_index = 0

        if self.top_visible_row_index != top_visible_row_index or self.hilighted_row_index != hilighted_row_index or self.hilighted_col_index != hilighted_col_index:
            self.top_visible_row_index = top_visible_row_index
            self.hilighted_row_index = hilighted_row_index
            self.hilighted_col_index = hilighted_col_index
            self.needs_render = True

    def run(self, stop_key_list: List[Keycodes] = None) -> ScrollPanelRunResult:
        self.show()
        self.window.timeout(-1)

        if stop_key_list is None:
            stop_key_list = [Keycodes.ESCAPE, Keycodes.RETURN]

        while True:
            self.render()
            curses.panel.update_panels()
            CURSES_STDSCR.refresh()

            key = self.window.getch()
            # CURSES_STDSCR.addstr(0, 0, 'key={}     '.format(key), curses.color_pair(COLOUR_RED_BLACK))

            if key == curses.KEY_BACKSPACE:
                key = Keycodes.BACKSPACE
            elif key == curses.KEY_DC:
                key = Keycodes.DELETE

            if key in [curses.KEY_UP, curses.KEY_DOWN, curses.KEY_LEFT, curses.KEY_RIGHT, curses.KEY_PPAGE, curses.KEY_NPAGE, curses.KEY_HOME, curses.KEY_END]:
                self.handle_keystroke(key)
            elif key in stop_key_list:
                row_index = self.hilighted_row_index
                col_index = self.hilighted_col_index
                row = self.rows[self.hilighted_row_index]
                col = row.columns[self.hilighted_col_index]
                text = col.text
                run_result = ScrollPanelRunResult(row_index=row_index, col_index=col_index, text=text, key=key)
                return run_result

    def pick_a_line_or_cancel(self, stop_key_list: List[Keycodes] = None):
        while True:
            run_result = self.run(stop_key_list)
            if run_result.key == Keycodes.ESCAPE:
                return None
            if run_result.key != Keycodes.RETURN:
                continue

            return run_result.row_index



class MessagePanel(ScrollingPanel):
    """Similar to the ScrollingPanel, but just displays a message and waits for user to press enter/escape.
       The message_lines can be a list of str/unicode or tuples of (str/unicode, colour) like this:
           message_panel = MessagePanel([('Exception occurred:', CursesColourBinding.COLOUR_BLACK_RED), ''])
    """
    def __init__(self, message_lines: Union[str, List[str], Tuple[str, CursesColourBinding], List[Tuple[str, CursesColourBinding]]] = '', width=None, height=None):
        super().__init__(rows=message_lines, width=width, height=height, show_immediately=True, hilighted_row_index=-1)

        if isinstance(message_lines, str):
            self.message_lines = [message_lines]
        else:
            self.message_lines = message_lines

    def append_message_lines(self, message_str_or_list: Union[List, str, HorizontalLine], trim_to_visible_window=False):
        if not self.message_lines:
            self.message_lines = list()

        if isinstance(message_str_or_list, str):
            self.message_lines.append(message_str_or_list)
        elif isinstance(message_str_or_list, HorizontalLine):
            self.message_lines.append(message_str_or_list)
        elif isinstance(message_str_or_list, list):
            self.message_lines.extend(message_str_or_list)

        if trim_to_visible_window and len(self.message_lines) > self.content_height:
            self.message_lines = self.message_lines[len(self.message_lines) - self.content_height:]

        self.set_rows(self.message_lines, hilighted_row=-1)
        self.redraw_refresh()

    def set_message_lines(self, new_message_lines):
        self.set_rows(new_message_lines, hilighted_row=-1)
        self.render(force=True)

    def redraw_refresh(self):
        self.render(force=True)
        curses.panel.update_panels()
        CURSES_STDSCR.refresh()

    def run(self, stop_key_list: List[Keycodes] = None):
        self.show()
        self.window.timeout(-1)

        while True:
            key = self.window.getch()

            if key == Keycodes.ESCAPE:
                self.hide()
                return False
            elif key == Keycodes.RETURN:
                self.hide()
                return True


class InputPanel:
    """Similar to the ScrollingPanel, but handles user input.
    """
    def __init__(self, prompt: str = '', default_value: str = None, entry_width: Optional[int] = None, allowed_input_chars: Optional[str] = None):
        if default_value is None:
            default_value = ''

        self.prompt = prompt
        self.prompt_width = len(self.prompt)
        self.num_rows = 1

        self.input_text = str(default_value)
        self.allowed_input_chars = allowed_input_chars or 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 !@#$%^&*(),<.>/?;:'"[{]}-_=+"
        self.needs_render = True

        stdscr_height, stdscr_width = CURSES_STDSCR.getmaxyx()

        self.entry_width = entry_width or stdscr_width // 4
        self.content_width = self.entry_width + self.prompt_width

        self.win_top = (stdscr_height - 2) // 2
        self.win_left = (stdscr_width - self.content_width) // 2
        self.win_width = self.content_width + 4
        self.win_height = 3

        self.window = curses.newwin(self.win_height, self.win_width, self.win_top, self.win_left)
        self.window.keypad(True)
        self.panel = curses.panel.new_panel(self.window)
        self.panel.hide()

        self.input_text_cursor_index = len(self.input_text)

        if self.input_text_cursor_index < self.entry_width:
            self.input_text_first_displayed_char_index = 0
        else:
            self.input_text_first_displayed_char_index = self.input_text_cursor_index - self.entry_width

    def __enter__(self):
        return self

    def __exit__(self, _type, _value, _traceback):
        self.hide()

    def hide(self):
        if self.panel:
            self.panel.hide()
            curses.panel.update_panels()
            CURSES_STDSCR.refresh()

    def show(self):
        if self.panel:
            self.panel.show()
            curses.panel.update_panels()
            CURSES_STDSCR.refresh()

    def render(self, force=False):
        if not (force or self.needs_render):
            return

        input_text_len = len(self.input_text)
        clipped_text = self.input_text[self.input_text_first_displayed_char_index:self.input_text_first_displayed_char_index + self.entry_width]
        cursor_char = self.input_text[self.input_text_cursor_index] if self.input_text_cursor_index < input_text_len else ' '
        cursor_index_from_left = self.input_text_cursor_index - self.input_text_first_displayed_char_index

        self.window.erase()
        self.window.border()
        self.window.addstr(1, 2, self.prompt, curses.color_pair(CursesColourBinding.COLOUR_CYAN_BLACK))
        self.window.addstr(1, 2 + self.prompt_width, clipped_text, curses.color_pair(CursesColourBinding.COLOUR_WHITE_BLACK))
        # self.window.addstr(1, 2 + self.prompt_width + len_clipped_text, ' ', curses.color_pair(CursesColourBinding.COLOUR_BLACK_WHITE))
        self.window.addstr(1, 2 + self.prompt_width + cursor_index_from_left, cursor_char, curses.color_pair(CursesColourBinding.COLOUR_BLACK_WHITE))

        self.needs_render = False

    def handle_keystroke(self, key):
        # LOGGER.info('handle_keystroke: %d', key)
        if key == curses.KEY_BACKSPACE or key == Keycodes.BACKSPACE:
            if self.input_text_cursor_index > 0:
                self.input_text = self.input_text[:self.input_text_cursor_index - 1] + self.input_text[self.input_text_cursor_index:]
                self.input_text_cursor_index -= 1
                if self.input_text_cursor_index < self.input_text_first_displayed_char_index:
                    self.input_text_first_displayed_char_index = self.input_text_cursor_index
                self.needs_render = True
        elif key == curses.KEY_DC or key == Keycodes.DELETE:
            if self.input_text_cursor_index >= 0:
                self.input_text = self.input_text[:self.input_text_cursor_index] + self.input_text[self.input_text_cursor_index + 1:]
                self.needs_render = True
        elif key == curses.KEY_LEFT:
            if self.input_text_cursor_index > 0:
                self.input_text_cursor_index -= 1
                if self.input_text_cursor_index < self.input_text_first_displayed_char_index:
                    self.input_text_first_displayed_char_index = self.input_text_cursor_index
                self.needs_render = True
        elif key == curses.KEY_RIGHT:
            if self.input_text_cursor_index < len(self.input_text):
                self.input_text_cursor_index += 1
                if self.input_text_cursor_index - self.input_text_first_displayed_char_index >= self.entry_width:
                    self.input_text_first_displayed_char_index += 1
                self.needs_render = True
        elif key == curses.KEY_HOME:
            self.input_text_cursor_index = 0
            self.input_text_first_displayed_char_index = 0
            self.needs_render = True
        elif key == curses.KEY_END:
            self.input_text_cursor_index = len(self.input_text)
            if self.input_text_cursor_index < self.entry_width:
                self.input_text_first_displayed_char_index = 0
            else:
                self.input_text_first_displayed_char_index = self.input_text_cursor_index - self.entry_width
            self.needs_render = True
        elif 0 <= key <= 255:
            char = chr(key)
            if char in self.allowed_input_chars:
                # self.input_text += chr(key)
                self.input_text = self.input_text[:self.input_text_cursor_index] + chr(key) + self.input_text[self.input_text_cursor_index:]
                self.input_text_cursor_index += 1
                if self.input_text_cursor_index - self.input_text_first_displayed_char_index >= self.entry_width:
                    self.input_text_first_displayed_char_index += 1
                self.needs_render = True

    def run(self):
        self.show()
        self.window.timeout(-1)

        while True:
            self.render()
            curses.panel.update_panels()
            CURSES_STDSCR.refresh()

            key = self.window.getch()

            if key == Keycodes.ESCAPE:
                return None
            elif key == Keycodes.RETURN:
                return self.input_text
            else:
                self.handle_keystroke(key)


class DialogBox:
    def __init__(self, prompt: Union[Row, List[Row], List[str], str], buttons_text: List[str] = None, show_immediately: bool = False):
        if buttons_text is None:
            buttons_text = ['OK']

        self.window = None
        self.panel = None
        self.needs_render = True

        self.prompt_rows: Optional[List[Row]] = None
        self.num_prompt_rows = 0
        self.buttons_text: Optional[List[str]] = None
        self.raw_buttons_text: Optional[List[str]] = None
        self.num_buttons = 0
        self.button_text_width = 0
        self.content_width = 0
        self.content_height = 0
        self.hilighted_button_index = 0

        self.set_prompt_and_buttons(prompt, buttons_text)

        stdscr_height, stdscr_width = CURSES_STDSCR.getmaxyx()

        self.top = (stdscr_height - 2) // 2
        self.left = (stdscr_width - self.content_width) // 2
        self.width = self.content_width + 4  # Leave a blank space at the left/right, and also account for the border
        self.height = self.content_height + 2  # Leave a blank space at the top/bottom, and also account for the border

        self.window = curses.newwin(self.height, self.width, self.top, self.left)
        self.window.keypad(True)
        self.panel = curses.panel.new_panel(self.window)
        self.panel.hide()

        if show_immediately:
            self.show()

    def __enter__(self):
        return self

    def __exit__(self, _type, _value, _traceback):
        self.hide()

    def set_prompt(self, prompt, refresh=False):
        # TODO: Resize window if necessary!

        if isinstance(prompt, list):
            self.prompt_rows = [p if isinstance(p, Row) else Row(p) for p in prompt]
        else:
            self.prompt_rows = [prompt if isinstance(prompt, Row) else Row(prompt)]
        self.num_prompt_rows = len(self.prompt_rows)
        self.content_height = self.num_prompt_rows + 2

        for row_i, row in enumerate(self.prompt_rows):
            row_width = sum(col.width for col in row.columns)
            self.content_width = max(self.content_width, row_width)

        self.needs_render = True

        if refresh:
            self.render()
            curses.panel.update_panels()
            CURSES_STDSCR.refresh()

    def set_prompt_and_buttons(self, prompt, buttons_text):
        # TODO: Resize window if necessary!

        self.raw_buttons_text = buttons_text[:]
        self.buttons_text = [f' [ {b} ] ' for b in buttons_text]
        self.num_buttons = len(self.buttons_text)
        self.button_text_width = sum(len(b) for b in self.buttons_text)
        self.content_width = self.button_text_width

        self.set_prompt(prompt)

    def hide(self):
        if self.panel:
            self.panel.hide()
            curses.panel.update_panels()
            CURSES_STDSCR.refresh()

    def show(self):
        if self.panel:
            self.render(force=True)
            self.panel.show()
            curses.panel.update_panels()
            CURSES_STDSCR.refresh()

    def render(self, force=False):
        if not (force or self.needs_render):
            return

        self.window.erase()
        self.window.border()

        for row_i, row in enumerate(self.prompt_rows):  # type: int, Row
            x = 2
            for col_i, col in enumerate(row.columns):  # type: int, Column
                text = col.text
                text_colour = col.colour

                if len(text) > self.content_width:
                    text = text[:self.content_width - 4] + u'...'

                self.window.addstr(1 + row_i, x, text, curses.color_pair(text_colour))
                x += len(text)

        x = 2 + self.content_width - self.button_text_width
        for i, button_text in enumerate(self.buttons_text):
            if i == self.hilighted_button_index:
                text_colour = CursesColourBinding.COLOUR_BLACK_YELLOW
            else:
                text_colour = CursesColourBinding.COLOUR_WHITE_BLACK

            self.window.addstr(1 + self.num_prompt_rows + 1, x, button_text, curses.color_pair(text_colour))
            x += len(button_text)

        self.needs_render = False

    def run(self, single_key=False):
        self.show()

        self.render()
        curses.panel.update_panels()
        CURSES_STDSCR.refresh()

        while True:
            result = None
            key = self.window.getch()

            if key == curses.KEY_LEFT and self.hilighted_button_index > 0:
                self.hilighted_button_index -= 1
                self.needs_render = True
            elif key == curses.KEY_RIGHT and self.hilighted_button_index < self.num_buttons - 1:
                self.hilighted_button_index += 1
                self.needs_render = True
            elif key == Keycodes.ESCAPE:
                result = ''
            elif key == Keycodes.RETURN:
                result = self.raw_buttons_text[self.hilighted_button_index]

            if self.needs_render:
                self.render()
                curses.panel.update_panels()
                CURSES_STDSCR.refresh()

            if single_key or result is not None:
                return result


def show_exception_details_dialog(exc_type, exc_value, exc_traceback):
    message_lines = [f'Caught an exception: {exc_value}']
    exception_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    for exception_line in exception_lines:
        for line in exception_line.split('\n'):
            if line.strip():
                message_lines.append(line)

    for line in message_lines:
        logging.error(line)

    with MessagePanel(message_lines) as message_panel:
        message_panel.run()
        return


def run_cancellable_thread(task: Callable, getch_function = None, cancel_keys: List = None, show_exception_dialog=True):
    if cancel_keys is None:
        cancel_keys = [Keycodes.ESCAPE]

    task_thread = SelectableThread(task)
    task_thread.start()

    sel = selectors.DefaultSelector()
    sel.register(task_thread.read_pipe_fd, selectors.EVENT_READ, 'PIPE')
    if getch_function:
        sel.register(sys.stdin, selectors.EVENT_READ, 'STDIN')

    try:
        while task_thread.is_alive():
            for selector_key, event_mask in sel.select():
                if getch_function and selector_key.data == 'STDIN':
                    key = getch_function()
                    if key in cancel_keys:
                        raise UserCancelException()
    finally:
        sel.unregister(task_thread.read_pipe_fd)
        if getch_function:
            sel.unregister(sys.stdin)
        sel.close()

    if task_thread.callable_exception_info_tuple:
        if show_exception_dialog:
            exc_type, exc_value, exc_traceback = task_thread.callable_exception_info_tuple
            show_exception_details_dialog(exc_type, exc_value, exc_traceback)
        raise AsyncThreadException()

    return task_thread.callable_result


def run_cancellable_thread_dialog(task: Callable, dialog_text: str):
    with DialogBox(prompt=dialog_text, buttons_text=['Cancel'], show_immediately=True) as dialog_box:
        callable_result = run_cancellable_thread(task, getch_function=dialog_box.window.getch, cancel_keys=[Keycodes.ESCAPE, Keycodes.RETURN])

    return callable_result


class MainMenu(ScrollingPanel):
    """A subclass of ScrollingPanel that displays a menu (i.e. list) of actions for the user to select.
       When the user presses return/enter, the callback associated with the highlighted menu item is invoked.
    """
    def __init__(self):
        super(MainMenu, self).__init__()

        self.menu_choices: List[Tuple[str, Callable]] = []
        self.logger: Optional[logging.Logger] = None

    def set_menu_choices(self):
        """Populate self.menu_choices with a list of tuples, (<menu item text>, <menu item callback>)"""
        self.menu_choices = []

    def quit_confirm(self):
        return True

    def run_modally(self):
        """Run modally, handling user keystrokes, and executing the callback when the user selects a menu item"""

        self.set_menu_choices()
        rows = [t[0] for t in self.menu_choices]
        self.set_rows(rows)

        while True:
            self.render()

            curses.panel.update_panels()
            CURSES_STDSCR.refresh()

            self.window.timeout(-1)
            key = self.window.getch()

            if key == Keycodes.ESCAPE:
                if self.quit_confirm():
                    self.hide()
                    return key
            elif key == Keycodes.RETURN:
                self.hide()

                try:
                    menu_choice_action = self.menu_choices[self.hilighted_row_index]
                    if menu_choice_action and menu_choice_action[1]:
                        menu_choice_action[1]()

                except Exception: # noqa PyBroadException
                    exception_dump_lines = traceback.format_exc().splitlines()
                    if self.logger:
                        for exception_line in exception_dump_lines:
                            self.logger.info(exception_line)
                    message_panel = MessagePanel([('Exception occurred:', CursesColourBinding.COLOUR_BLACK_RED), ''] + exception_dump_lines)
                    message_panel.run()

                self.show()

            else:
                self.handle_keystroke(key)


class TUITextItem:
    def __init__(self, text: Text):
        self.text: Text = text

    def __repr__(self):
        return self.text

class TUITextChoiceItem:
    def __init__(self, text: Text, choices: List[Text]):
        self.text: Text = text
        self.choices : List[Text] = choices

    def __repr__(self):
        return f'({self.text}, {self.choices})'

class TUIListItem:
    def __init__(self, items: List):
        self.items_list : List = items

    def __repr__(self):
        return repr(self.items_list)

class TUIDictItem:
    def __init__(self, items: Dict):
        self.items_dict : Dict = items

    def __repr__(self):
        return repr(self.items_dict)

TUIEditableItem = TUITextItem | TUITextChoiceItem | TUIListItem | TUIDictItem

class TUILabelItem:
    def __init__(self, label: Text, item: TUIEditableItem):
        self.label: Text = label
        self.item: TUIEditableItem = item

    def __str__(self):
        if isinstance(self.item, TUILabelItem):
            # Ooh, recursion to format the string...
            return f'{self.label}: {self.item}'
        elif isinstance(self.item, TUITextItem) or isinstance(self.item, TUITextChoiceItem):
            return f'{self.label}: {self.item.text}'
        elif isinstance(self.item, TUIDictItem):
            return f'{self.label}: {{ ... }}'
        elif isinstance(self.item, TUIListItem):
            return f'{self.label}: [ ... ]'

    def __repr__(self):
        return f'{self.label}: {self.item}'


def tui_edit_choice_item(tui_choice_item: TUITextChoiceItem) -> Tuple[Optional[int], bool]:
    choices_list = tui_choice_item.choices
    hilighted_row_index = choices_list.index(tui_choice_item.text) if tui_choice_item.text in choices_list else 0
    with ScrollingPanel(rows=choices_list, hilighted_row_index=hilighted_row_index) as scrolling_panel:
        while True:
            run_result = scrolling_panel.run()
            if run_result.key == Keycodes.ESCAPE:
                # User cancelled pick
                return None, False
            elif run_result.key == Keycodes.RETURN:
                # User picked a value
                item_changed = tui_choice_item.text != choices_list[run_result.row_index]
                tui_choice_item.text = choices_list[run_result.row_index]
                return run_result.row_index, item_changed

def tui_edit_text_item(tui_text_item: TUITextItem, edit_prompt: Text = '') -> Tuple[Optional[int], bool]:
    with InputPanel(prompt=edit_prompt, default_value=tui_text_item.text) as input_panel:
        new_value = input_panel.run()
        if new_value is not None:
            tui_text_item.text = new_value
            return 0, True
        else:
            return None, False

def tui_edit_list_of_items(tui_list_item: TUIListItem) -> Tuple[Optional[int], bool]:
    def setup_display_rows(items_list):
        display_list = list()
        for tui_item in items_list:
            if isinstance(tui_item, TUILabelItem):
                # Let the TUILabelItem format the display string
                display_list.append(str(tui_item))
            elif isinstance(tui_item, TUITextItem) or isinstance(tui_item, TUITextChoiceItem):
                display_list.append(tui_item.text)
            elif isinstance(tui_item, TUIDictItem):
                display_list.append('{ ... }')
            elif isinstance(tui_item, TUIListItem):
                display_list.append('[ ... ]')
        return display_list

    data_changed_final = False
    display_rows = setup_display_rows(tui_list_item.items_list)

    with ScrollingPanel(rows=display_rows) as scrolling_panel:
        while True:
            # Wait for the user to do something
            run_result = scrolling_panel.run(stop_key_list = [Keycodes.ESCAPE, Keycodes.RETURN, Keycodes.BACKSPACE, Keycodes.DELETE])
            edit_item = tui_list_item.items_list[run_result.row_index]
            refresh_display = False

            if run_result.key == Keycodes.ESCAPE:
                # User cancelled, so GTFO
                return None, data_changed_final
            elif run_result.key == Keycodes.BACKSPACE or run_result.key == Keycodes.DELETE:
                target_item = edit_item.item if isinstance(edit_item, TUILabelItem) else edit_item
                if isinstance(target_item, TUITextItem) or isinstance(target_item, TUITextChoiceItem):
                    data_changed = target_item.text != ''
                    target_item.text = ''
                    if data_changed:
                        data_changed_final = True
                        refresh_display = True
            elif run_result.key == Keycodes.RETURN:
                return_code, data_changed = tui_edit_single_item(edit_item)
                if data_changed:
                    data_changed_final = True
                    refresh_display = True

            # Refresh the display with the new values, if needed
            if refresh_display:
                display_rows = setup_display_rows(tui_list_item.items_list)
                scrolling_panel.set_rows(display_rows, run_result.row_index)

def tui_edit_dict_item(tui_dict_item: TUIDictItem) -> Tuple[Optional[int], bool]:
    # Set up a list of TUILabelItem objects and then use tui_edit_list_of_items to edit it
    tui_labeled_items_list = [TUILabelItem(key, value) for key, value in tui_dict_item.items_dict.items()]
    tui_list_item = TUIListItem(tui_labeled_items_list)
    return_code, data_changed = tui_edit_list_of_items(tui_list_item)

    return return_code, data_changed

def tui_edit_single_item(edit_item: TUIEditableItem, edit_prompt: Text = '') -> Tuple[Optional[int], bool]:
    if isinstance(edit_item, TUILabelItem):
        return tui_edit_single_item(edit_item.item, edit_prompt=f'{edit_item.label}: ')
    if isinstance(edit_item, TUITextItem):
        # Edit the text item
        return tui_edit_text_item(edit_item, edit_prompt)
    elif isinstance(edit_item, TUITextChoiceItem):
        # Pick from a list of choices
        return tui_edit_choice_item(edit_item)
    elif isinstance(edit_item, TUIListItem):
        # Edit the list of items
        return tui_edit_list_of_items(edit_item)
    elif isinstance(edit_item, TUIDictItem):
        # Edit the dict of items
        return tui_edit_dict_item(edit_item)
    else:
        return None, False

def tui_edit_json(json_obj):
    def convert_json_item_to_tui(json_item):
        if isinstance(json_item, tuple):
            return TUITextChoiceItem(str(json_item[0]), [str(choice) for choice in json_item[1]])
        elif isinstance(json_item, str) or isinstance(json_item, int) or isinstance(json_item, float):
            return TUITextItem(str(json_item))
        elif isinstance(json_item, list):
            # tui_list = [convert_json_item_to_tui(list_item) for list_item in json_item]
            tui_list = [TUILabelItem(str(i), convert_json_item_to_tui(list_item)) for i, list_item in enumerate(json_item)]
            return TUIListItem(tui_list)
        elif isinstance(json_item, dict):
            tui_dict = {key: convert_json_item_to_tui(value) for key, value in json_item.items()}
            return TUIDictItem(tui_dict)
        else:
            raise Exception('Unhandled json item [%s]: %s', type(json_item), json_item)

    def convert_tui_item_to_json(tui_item):
        if isinstance(tui_item, TUITextChoiceItem) or isinstance(tui_item, TUITextItem):
            return tui_item.text
        elif isinstance(tui_item, TUIListItem):
            return [convert_tui_item_to_json(list_item) for list_item in tui_item.items_list]
        elif isinstance(tui_item, TUIDictItem):
            return {key: convert_tui_item_to_json(value) for key, value in tui_item.items_dict.items()}
        elif isinstance(tui_item, TUILabelItem):
            return convert_tui_item_to_json(tui_item.item)
        else:
            raise Exception('Unhandled tui item [%s]: %s', type(tui_item), tui_item)

    # Convert a JSON dict/list into TUI objects, edit them, then return the final JSON
    tui_edit_obj = convert_json_item_to_tui(json_obj)
    tui_edit_single_item(tui_edit_obj)
    final_json = convert_tui_item_to_json(tui_edit_obj)

    return final_json


def interactive_main(stdscr: CursesStdscrType, main_menu_cls: type) -> None:
    # LOGGER.info('type(stdscr) = %s', str(type(stdscr)))  # Weird: type(stdscr) = <type '_curses.curses window'>

    # Initialize all the curses stuff we need
    global CURSES_STDSCR
    CURSES_STDSCR = stdscr

    # # Figure out what the preferred locale encoding is so we can use that when asking curses to render unicode strings
    # locale.setlocale(locale.LC_ALL, '')
    #
    # global PREFERRED_ENCODING
    # PREFERRED_ENCODING = locale.getpreferredencoding()

    curses.curs_set(False)

    curses.start_color()
    curses.init_pair(CursesColourBinding.COLOUR_CYAN_BLACK, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(CursesColourBinding.COLOUR_RED_BLACK, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(CursesColourBinding.COLOUR_BLACK_WHITE, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(CursesColourBinding.COLOUR_YELLOW_BLACK, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(CursesColourBinding.COLOUR_BLACK_YELLOW, curses.COLOR_BLACK, curses.COLOR_YELLOW)
    curses.init_pair(CursesColourBinding.COLOUR_BLACK_RED, curses.COLOR_BLACK, curses.COLOR_RED)

    CURSES_STDSCR.clear()

    main_menu = main_menu_cls()
    main_menu.run_modally()

    # Calling hide() seems to trigger an error, so don't do it?
    # main_menu.hide()


def console_gui_main(main_menu_cls: type) -> None:
    # Set the ESCDELAY envar since curses does funky stuff with escape key sequences by default, but we want to get the escape key immediately
    # This has to happen BEFORE the call to curses.wrapper() below
    os.environ.setdefault('ESCDELAY', '25')

    # LOGGER.info('Begin interactive mode')
    curses.wrapper(interactive_main, main_menu_cls)
    # LOGGER.info('End interactive mode')
