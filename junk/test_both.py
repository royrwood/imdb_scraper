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

print(f'type of r_fd = {type(r_fd)}')
print(f'type of w_fd = {type(w_fd)}')

print('Forking...')
process_id = os.fork()

if process_id:
    print('PARENT: Closing w_fd')
    os.close(w_fd)

    print('PARENT: Opening r_file')
    # fcntl.fcntl(r_fd, fcntl.F_SETFL, os.O_NONBLOCK)
    # r_file = os.fdopen(r_fd, 'r')

    print('PARENT: Creating selector')
    sel = selectors.DefaultSelector()
    # sel.register(r_file, selectors.EVENT_READ, 'PIPE')
    sel.register(r_fd, selectors.EVENT_READ, 'PIPE')
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
        read_buffer = ''
        print('PARENT: Waiting for data')
        while keep_going:
            events = sel.select(0.5)
            for selector_key, event_mask in events:
                if selector_key.data == 'PIPE':
                    print('PARENT: Reading r_file')
                    text = os.read(r_fd, 1024)
                    # text = r_file.read()
                    print(f'PARENT: Read {len(text)} bytes from r_file ({repr(text)})')
                    if not text:
                        keep_going = False
                    read_buffer += text.decode('ascii')
                    if '\n' in read_buffer:
                        newline_i = read_buffer.find('\n')
                        read_message = read_buffer[:newline_i]
                        print(f'PARENT: Read message "{read_message}" from r_file')
                        read_buffer = read_buffer[newline_i + 1:]
                        # keep_going = False
                elif selector_key.data == 'STDIN':
                    char = sys.stdin.read(1)
                    print(f'PARENT: Read char {repr(char)} from stdin')
                else:
                    print(f'PARENT: Unknown selector key.data')

    # sel.unregister(r_file)
    sel.unregister(r_fd)
    sel.close()

    print('PARENT: Exiting')
    sys.exit(0)

else:
    print('CHILD: Closing r_fd')
    os.close(r_fd)

    print('CHILD: Sleeping')
    time.sleep(2)
    print('CHILD: Writing w_fd')
    os.write(w_fd, bytes('CHILD\n', 'ascii'))
    time.sleep(2)
    print('CHILD: Writing w_fd')
    os.write(w_fd, bytes('SAYS\n', 'ascii'))
    time.sleep(2)
    print('CHILD: Writing w_fd')
    os.write(w_fd, bytes('HELLO\n', 'ascii'))
    print('CHILD: Closing w_fd')
    os.close(w_fd)

    # print('CHILD: Opening w_file')
    # w_file = os.fdopen(w_fd, 'w')
    # print('CHILD: Sleeping')
    # time.sleep(2)
    # print('CHILD: Writing w_file')
    # w_file.write('CHILD\n')
    # w_file.flush()
    # time.sleep(2)
    # print('CHILD: Writing w_file')
    # w_file.write('SAYS\n')
    # w_file.flush()
    # time.sleep(2)
    # print('CHILD: Writing w_file')
    # w_file.write('HELLO\n')
    # w_file.flush()
    # print('CHILD: Closing w_file')
    # w_file.close()
    #
    print('CHILD: Exiting')
    sys.exit(0)
