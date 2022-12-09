#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from imdb_scraper.curses_gui import LOGGER
from imdb_scraper.curses_gui import MainMenu
from imdb_scraper.curses_gui import console_gui_main


class MyMenu(MainMenu):
    def __init__(self):
        super(MyMenu, self).__init__()

    def set_menu_choices(self):
        self.menu_choices = []
        self.menu_choices.append(('Some menu choice', self.class_callback_function))
        self.menu_choices.append(('Another menu choice', plain_function_callback))

    def class_callback_function(self):
        LOGGER.info('Callback for some menu choice (class method callback)')


def plain_function_callback():
    LOGGER.info('Callback for another menu choice (plain function callback)')


if __name__ == '__main__':
    console_gui_main(MyMenu)
