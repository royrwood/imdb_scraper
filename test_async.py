#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import fcntl
import logging
import os
import selectors
import sys
import termios
import time
import tty


class raw_nonblocking(object):
    def __init__(self, stream):
        self.stream = stream
        self.fd = self.stream.fileno()

    def __enter__(self):
        self.original_stty = termios.tcgetattr(self.stream)
        tty.setcbreak(self.stream)
        self.orig_fl = fcntl.fcntl(self.fd, fcntl.F_GETFL)
        fcntl.fcntl(self.fd, fcntl.F_SETFL, self.orig_fl | os.O_NONBLOCK)

    def __exit__(self, exception_type, exception_value, exception_traceback):
        termios.tcsetattr(self.stream, termios.TCSANOW, self.original_stty)
        fcntl.fcntl(self.fd, fcntl.F_SETFL, self.orig_fl)


if __name__ == '__main__':
    logging.basicConfig(format='[%(process)d]:%(levelname)s:%(funcName)s:%(lineno)d: %(message)s', level=logging.INFO)

    logging.info('Starting up...')

    sel = selectors.DefaultSelector()
    sel.register(sys.stdin, selectors.EVENT_READ, 'STDIN')

    with raw_nonblocking(sys.stdin):
        keep_going = True

        while keep_going:
            logging.info('Sleeping for 5 sec...')
            time.sleep(5.0)

            logging.info('Waiting for sys.stdin readiness...')
            events = sel.select()
            for selector_key, event_mask in events:
                if selector_key.data == 'STDIN':
                    logging.info(f'Reading sys.stdin')
                    text = sys.stdin.read()
                    termios.tcflush(sys.stdin, termios.TCIOFLUSH)
                    logging.info(f'Read {len(text)} bytes from sys.stdin: {text}')

    sel.unregister(sys.stdin)
    sel.close()
