import fcntl
import sys
import os
import time
import tty
import termios
import select
import sys


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


with raw(sys.stdin):
    with nonblocking(sys.stdin):
        while True:
            print('Calling select...')
            if select.select([sys.stdin], [], [], 1.0) == ([sys.stdin], [], []):
                c = sys.stdin.read(1)
                print(f'Read char "{repr(c)}"')

            # if c:
            #     print(repr(c))
            # else:
            #     print('not ready')
            # time.sleep(.1)
