#!/usr/bin/python

import fcntl
import sys
import os
import time
import tty
import termios
import selectors


class raw(object):
    def __init__(self, stream):
        self.stream = stream
        self.fd = self.stream.fileno()

    def __enter__(self):
        self.original_stty = termios.tcgetattr(self.stream)
        tty.setcbreak(self.stream)

    def __exit__(self, exception_type, exception_value, exception_traceback):
        termios.tcsetattr(self.stream, termios.TCSANOW, self.original_stty)


class nonblocking(object):
    def __init__(self, stream):
        self.stream = stream
        self.fd = self.stream.fileno()

    def __enter__(self):
        self.orig_fl = fcntl.fcntl(self.fd, fcntl.F_GETFL)
        fcntl.fcntl(self.fd, fcntl.F_SETFL, self.orig_fl | os.O_NONBLOCK)

    def __exit__(self, *args):
        fcntl.fcntl(self.fd, fcntl.F_SETFL, self.orig_fl)


print('Creating pipe...')
r_fd, w_fd = os.pipe()

print('Forking...')
process_id = os.fork()

if process_id:
    print('PARENT: Closing w_fd')
    os.close(w_fd)

    print('PARENT: Opening r_file')
    r_file = os.fdopen(r_fd, 'r')

    print('PARENT: Creating selector')
    sel = selectors.DefaultSelector()
    sel.register(r_file, selectors.EVENT_READ, 'PIPE')
    sel.register(sys.stdin, selectors.EVENT_READ, 'STDIN')

    # with raw(sys.stdin):
    #     with nonblocking(sys.stdin):
    #         keep_going = True
    #         while keep_going:
    #             print('PARENT: Waiting for data')
    #             events = sel.select(0.5)
    #             for selector_key, event_mask in events:
    #                 if selector_key.data == 'PIPE':
    #                     print('PARENT: Reading r_file')
    #                     text = r_file.read()
    #                     print(f'PARENT: Read "{text}"')
    #                     keep_going = False
    #                 elif selector_key.data == 'STDIN':
    #                     char = sys.stdin.read(1)
    #                     print(f'Read char "{repr(char)}"')

    with raw(sys.stdin):
        keep_going = True
        while keep_going:
            print('PARENT: Waiting for data')
            events = sel.select(0.5)
            for selector_key, event_mask in events:
                if selector_key.data == 'PIPE':
                    print('PARENT: Reading r_file')
                    text = r_file.read()
                    print(f'PARENT: Read "{text}"')
                    keep_going = False
                elif selector_key.data == 'STDIN':
                    char = sys.stdin.read(1)
                    print(f'Read char "{repr(char)}"')

    sel.unregister(r_file)
    sel.close()

    sys.exit(0)

else:
    print('CHILD: Closing r_fd')
    os.close(r_fd)

    print('CHILD: Opening w_file')
    w_file = os.fdopen(w_fd, 'w')
    print('CHILD: Sleeping')
    time.sleep(5)
    print('CHILD: Writing w_file')
    w_file.write('CHILD SAYS HELLO')
    sys.exit(0)
