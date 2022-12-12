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


import curses
import curses.panel
import logging
import os
import traceback
from enum import IntEnum, unique
from typing import List, Tuple, Callable, Union, Optional


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


class Column:
    """An object to represent a column/field in a row in a ScrollingPanel.
       If the column width is not specified, it defaults to the length of the text.
    """
    def __init__(self, text='', colour=CursesColourBinding.COLOUR_WHITE_BLACK, width=None):
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
    def __init__(self, row_content: Union[str, List] = ''):
        if isinstance(row_content, Column):
            self.columns = [row_content]
        elif isinstance(row_content, str):
            self.columns = [Column(text=row_content)]
        elif isinstance(row_content, list):
            self.columns = list()
            for i, rc in enumerate(row_content):
                if isinstance(rc, Column):
                    self.columns.append(rc)
                elif isinstance(rc, str):
                    self.columns.append(Column(text=rc))
                else:
                    raise Exception('Invalid row_content element %d, type %s', i, type(rc))
        else:
            raise Exception('Invalid row_content type %s', type(row_content))


class HorizontalLine(Row):
    """A row of this type will be rendered as a horizontal line.
    """
    def __init__(self):
        super(HorizontalLine, self).__init__()


class ScrollPanelRunResult:
    """When a ScrollPanel exits (e.g. user presses return or escape), an object of this type is returned.
    """
    def __init__(self, row_index, col_index, text, key):
        self.row_index = row_index
        self.col_index = col_index
        self.text = text
        self.key = key


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
    def __init__(self, rows=None, top=None, left=None, width=None, height=None, draw_border=True, header_row=None, grid_mode=False, select_grid_cells=False, inner_padding=False, debug_name=None):
        self.draw_border = draw_border

        self.debug_name = debug_name

        self.grid_mode = grid_mode
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
        self.hilighted_row_index = 0
        self.hilighted_col_index = 0
        self.height = 0
        self.width = 0
        self.top = 0
        self.left = 0
        self.content_top = 0
        self.content_left = 0
        self.content_height = 0
        self.content_width = 0
        self.message_lines = None

        self.set_header(header_row)
        self.set_rows(rows)
        self.set_geometry()

    def __enter__(self):
        return self

    def __exit__(self, _type, _value, _traceback):
        self.hide()

    def set_header(self, header_row):
        if type(header_row) is Row:
            self.header_row = header_row
            self.num_header_rows = 1
        elif header_row:
            self.header_row = Row([Column(header_row)])
            self.num_header_rows = 1
        else:
            self.header_row = None
            self.num_header_rows = 0

    def set_rows(self, new_rows):
        rows = []

        self.column_widths = list()
        
        if self.header_row:
            for column in self.header_row.columns:
                self.column_widths.append(column.width)

        if new_rows:
            for current_row in new_rows:
                if isinstance(current_row, HorizontalLine):
                    row = current_row
                elif isinstance(current_row, Row):
                    row = current_row
                else:
                    row = Row(row_content=current_row)

                rows.append(row)

                for i, column in enumerate(row.columns):
                    if i >= len(self.column_widths):
                        self.column_widths.append(column.width)
                    else:
                        self.column_widths[i] = max(self.column_widths[i], column.width)

            self.num_cols = len(self.column_widths)

            if self.inner_padding:
                for i in range(self.num_cols - 1):
                    self.column_widths[i] += 1

            if self.grid_mode:
                if self.header_row:
                    for i, column in enumerate(self.header_row.columns):
                        column.width = self.column_widths[i]

                for row in rows:
                    for i, column in enumerate(row.columns):
                        column.width = self.column_widths[i]

        self.rows = rows
        self.num_rows = len(self.rows)
        self.num_cols = len(self.column_widths)
        self.rows_max_width = sum(self.column_widths)
        self.needs_render = True
        self.top_visible_row_index = 0
        self.hilighted_row_index = 0
        self.hilighted_col_index = 0

        # Since the row contents have changed, we need to recalculate the window geometry
        self.set_geometry()

    def set_hilighted_row(self, new_hilighted_row):
        if self.hilighted_row_index != new_hilighted_row:
            self.needs_render = True

        self.hilighted_row_index = new_hilighted_row

    def reset_geometry(self):
        self.set_geometry()

    def set_geometry(self, visible=True):
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

        if self.window:
            del self.window

        # LOGGER.info('debug_name=%s, self.height=%s, self.width=%s, self.top=%s, self.left=%s', self.debug_name, self.height, self.width, self.top, self.left)
        self.window = curses.newwin(self.height, self.width, self.top, self.left)
        self.window.keypad(True)

        if self.panel:
            del self.panel

        self.panel = curses.panel.new_panel(self.window)

        if visible:
            self.panel.show()
        else:
            self.panel.hide()

        self.content_top = 1 + self.num_header_rows  # Leave 1 row for the border and then a row for the header, if there is one
        self.content_left = 2  # Left/right are indented by a space, and there is a border
        self.content_height = self.height - 2 - self.num_header_rows  # Account for top/bottom border and header
        self.content_width = self.width - 4  # Account for left/right border and a space on the left/right

    def hide(self):
        if self.panel:
            self.panel.hide()
            curses.panel.update_panels()
            CURSES_STDSCR.refresh()

    def show(self):
        if self.panel:
            self.set_geometry()
            self.render()
            self.panel.show()
            curses.panel.update_panels()
            CURSES_STDSCR.refresh()

    def render(self, force=False):
        if not (force or self.needs_render):
            return

        self.window.erase()

        if self.draw_border:
            self.window.border()

        if self.header_row:
            chars_rendered = 0
            for column in self.header_row.columns:
                text_colour = column.colour
                raw_text = column.text
                column_width = column.width
                padded_text = f'{raw_text: <{column_width}}'
                x = self.content_left + chars_rendered
                self.window.addstr(1, x, padded_text, curses.color_pair(text_colour))
                chars_rendered += column_width

        for ri in range(0, self.content_height):
            row_index = self.top_visible_row_index + ri
            y = self.content_top + ri

            if row_index >= self.num_rows:
                text_colour = CursesColourBinding.COLOUR_WHITE_BLACK
                raw_text = ''
                padded_text = u'{raw_text: <{width}}'.format(raw_text=raw_text, width=self.content_width)
                self.window.addstr(y, self.content_left, padded_text, curses.color_pair(text_colour))
                continue

            row = self.rows[row_index]

            if isinstance(row, HorizontalLine):
                x = self.content_left
                y = self.content_top + ri
                if row_index == self.hilighted_row_index:
                    text_colour = CursesColourBinding.COLOUR_BLACK_YELLOW
                else:
                    text_colour = row.columns[0].colour
                self.window.hline(y, x, curses.ACS_HLINE, self.content_width, curses.color_pair(text_colour))
                continue

            chars_rendered = 0

            for ci, column in enumerate(row.columns):
                raw_text = column.text
                column_width = column.width

                if column_width > self.content_width:
                    raw_text = raw_text[:self.content_width - 4] + u'...'
                    column_width = len(raw_text)

                if row_index == self.hilighted_row_index and (ci == self.hilighted_col_index or not self.select_grid_cells):
                    text_colour = CursesColourBinding.COLOUR_BLACK_YELLOW

                    # If last column of the hilighted row, pad the width out to the max content width
                    if ci + 1 == len(row.columns):
                        column_width = self.content_width - chars_rendered
                else:
                    # Shouldn't this be column.colour.value?
                    text_colour = column.colour

                padded_text = f'{raw_text: <{column_width}}'
                x = self.content_left + chars_rendered
                self.window.addstr(y, x, padded_text, curses.color_pair(text_colour))
                chars_rendered += column_width

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

        if stop_key_list is None:
            stop_key_list = [Keycodes.ESCAPE, Keycodes.RETURN]

        while True:
            self.render()
            curses.panel.update_panels()
            CURSES_STDSCR.refresh()

            key = self.window.getch()
            # CURSES_STDSCR.addstr(0, 0, 'key={}     '.format(key), curses.color_pair(COLOUR_RED_BLACK))

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


class MessagePanel:
    """Similar to the ScrollingPanel, but just displays a message and waits for user to press enter/escape.
       The message_lines can be a list of str/unicode or tuples of (str/unicode, colour) like this:
           message_panel = MessagePanel([('Exception occurred:', CursesColourBinding.COLOUR_BLACK_RED), ''])
    """
    def __init__(self, message_lines=None):
        self.window = None
        self.panel = None
        self.message_lines = []
        self.num_rows = 0
        self.rows_max_width = 0
        self.needs_render = True
        self.height = 0
        self.width = 0
        self.top = 0
        self.left = 0
        self.content_top = 0
        self.content_left = 0
        self.content_height = 0
        self.content_width = 0

        self.stdscr_height, self.stdscr_width = CURSES_STDSCR.getmaxyx()  # If/when we eventually handle dynamic screen sizing, this will need to be updated

        if message_lines is None:
            message_lines = list()
        elif isinstance(message_lines, str):
            message_lines = [message_lines]

        self.set_message_lines(message_lines)
        self.show()

    def __enter__(self):
        return self

    def __exit__(self, _type, _value, _traceback):
        self.hide()

    def append_message_lines(self, message_str_or_list: Union[List, str]):
        if not self.message_lines:
            self.message_lines = list()

        new_message_lines = self.message_lines[:]
        if isinstance(message_str_or_list, str):
            new_message_lines.append(message_str_or_list)
        elif isinstance(message_str_or_list, list):
            new_message_lines.extend(message_str_or_list)
        self.set_message_lines(new_message_lines)

    def set_message_lines(self, new_message_lines):
        self.message_lines = new_message_lines[:]
        self.num_rows = len(self.message_lines)
        self.rows_max_width = 0

        for message_line in self.message_lines:
            if isinstance(message_line, str):
                len_message_line = len(message_line)
            elif isinstance(message_line, tuple):
                len_message_line = len(message_line[0])
            else:
                len_message_line = 0

            if len_message_line > self.rows_max_width:
                self.rows_max_width = len(message_line)

        self.height = min(self.stdscr_height, self.num_rows + 2)
        self.width = min(self.stdscr_width, self.rows_max_width + 4)  # Leave a blank space at the left/right, and also account for the border
        self.top = int((self.stdscr_height - self.height) // 2)
        self.left = int((self.stdscr_width - self.width) // 2)

        if self.window:
            del self.window

        self.window = curses.newwin(self.height, self.width, self.top, self.left)
        self.window.keypad(True)

        if self.panel:
            del self.panel

        self.panel = curses.panel.new_panel(self.window)

        self.content_top = 1  # Leave 1 row for the border
        self.content_left = 2  # Left/right are indented by a space, and there is a border
        self.content_height = self.height - 2  # Account for top/bottom border and header
        self.content_width = self.width - 4  # Account for left/right border and a space on the left/right

        self.needs_render = True
        self.show()

    def hide(self):
        if self.panel:
            self.panel.hide()
            curses.panel.update_panels()
            CURSES_STDSCR.refresh()

    def show(self):
        if self.panel:
            self.panel.show()
            self.render()
            curses.panel.update_panels()
            CURSES_STDSCR.refresh()

    def render(self, force=False):
        if not (force or self.needs_render):
            return

        self.window.erase()
        self.window.border()

        max_lines_to_render = min(len(self.message_lines), self.content_height)
        for i in range(max_lines_to_render):
            message_line = self.message_lines[i]

            if isinstance(message_line, tuple):
                raw_text = message_line[0]
            elif isinstance(message_line, HorizontalLine):
                text_colour = CursesColourBinding.COLOUR_WHITE_BLACK
                self.window.hline(1 + i, 2, curses.ACS_HLINE, self.content_width, curses.color_pair(text_colour))
                continue
            else:
                raw_text = message_line

            if i == max_lines_to_render - 1 and max_lines_to_render < len(self.message_lines):
                raw_text = '...'

            if len(raw_text) > self.content_width:
                raw_text = raw_text[:self.content_width - 4] + u'...'

            if type(message_line) is tuple:
                self.window.addstr(1 + i, 2, raw_text, curses.color_pair(message_line[1]))
            else:
                # LOGGER.info('ROYDEBUG: raw_text="{}"'.format(raw_text))
                self.window.addstr(1 + i, 2, raw_text, curses.color_pair(CursesColourBinding.COLOUR_WHITE_BLACK))

        self.needs_render = False

    def run(self):
        self.show()

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
    def __init__(self, prompt='', default_value=u'', entry_width=None, allowed_input_chars=None):
        self.prompt = prompt
        self.prompt_width = len(self.prompt)
        self.num_rows = 1

        self.input_text = default_value
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
        elif key == Keycodes.DELETE:
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
    def __init__(self, prompt=None, buttons_text=None):
        self.window = None
        self.panel = None
        self.needs_render = True

        self.prompt_rows = None
        self.num_prompt_rows = 0
        self.buttons_text = None
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

    def __enter__(self):
        return self

    def __exit__(self, _type, _value, _traceback):
        self.hide()

    def set_prompt_and_buttons(self, prompt, buttons_text):
        self.buttons_text = [f' {b} ' for b in buttons_text]
        self.num_buttons = len(self.buttons_text)
        self.button_text_width = sum(len(b) for b in self.buttons_text)
        self.content_width = self.button_text_width

        if isinstance(prompt, list):
            self.prompt_rows = [p if isinstance(p, Row) else Row(p) for p in prompt]
        else:
            self.prompt_rows = [prompt if isinstance(prompt, Row) else Row(prompt)]
        self.num_prompt_rows = len(self.prompt_rows)
        self.content_height = self.num_prompt_rows + 2

        for row_i, row in enumerate(self.prompt_rows):  # type: int, Row
            row_width = sum(col.width for col in row.columns)
            self.content_width = max(self.content_width, row_width)

    def hide(self):
        if self.panel:
            self.panel.hide()
            curses.panel.update_panels()
            CURSES_STDSCR.refresh()

    def show(self):
        if self.panel:
            self.render()
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

    def run(self):
        self.show()

        while True:
            self.render()
            curses.panel.update_panels()
            CURSES_STDSCR.refresh()

            key = self.window.getch()
            if key == curses.KEY_LEFT and self.hilighted_button_index > 0:
                self.hilighted_button_index -= 1
                self.needs_render = True
            elif key == curses.KEY_RIGHT and self.hilighted_button_index < self.num_buttons - 1:
                self.hilighted_button_index += 1
                self.needs_render = True
            elif key == Keycodes.ESCAPE:
                return None
            elif key == Keycodes.RETURN:
                return self.hilighted_button_index


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
