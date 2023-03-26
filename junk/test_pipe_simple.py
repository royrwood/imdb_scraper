#!/usr/bin/python

import sys
import os
import time
import tty
import termios
import selectors


class tty_setcbreak:
    def __init__(self, stream):
        self.stream = stream
        self.stream_fd = self.stream.fileno()
        self.original_stream_attr = None

    def __enter__(self):
        self.original_stream_attr = termios.tcgetattr(self.stream)
        tty.setcbreak(self.stream)

    def __exit__(self, exception_type, exception_value, exception_traceback):
        termios.tcsetattr(self.stream, termios.TCSANOW, self.original_stream_attr)


print(f'Show type(sys.stdin) = {type(sys.stdin)}')
print(f'Show sys.stdin.fileno() = {sys.stdin.fileno()}')

print('Creating pipe...')
r_fd, w_fd = os.pipe()

print('Forking...')
process_id = os.fork()

if process_id:
    print('PARENT: Closing w_fd')
    os.close(w_fd)

    print('PARENT: Creating selector')
    sel = selectors.DefaultSelector()
    sel.register(r_fd, selectors.EVENT_READ, 'PIPE')
    sel.register(sys.stdin, selectors.EVENT_READ, 'STDIN')

    with tty_setcbreak(sys.stdin):
        keep_going = True
        read_buffer = ''
        print('PARENT: Waiting for data')
        while keep_going:
            events = sel.select(0.5)

            if not events:
                print('PARENT: No data ready for reading')
                continue

            for selector_key, event_mask in events:
                if selector_key.data == 'PIPE':
                    print('PARENT: Reading r_fd')
                    text = os.read(r_fd, 1024)
                    print(f'PARENT: Read {len(text)} bytes from r_fd ({repr(text)})')
                    if not text:
                        keep_going = False
                        continue

                    read_buffer += text.decode('ascii')
                    if '\n' in read_buffer:
                        newline_i = read_buffer.find('\n')
                        read_message = read_buffer[:newline_i]
                        print(f'PARENT: Read message "{read_message}" from r_fd')
                        read_buffer = read_buffer[newline_i + 1:]
                elif selector_key.data == 'STDIN':
                    char = sys.stdin.read(1)
                    print(f'PARENT: Read char {repr(char)} from stdin')
                else:
                    print(f'PARENT: Unknown selector key.data')

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

    print('CHILD: Exiting')
    sys.exit(0)


# Interesting selectable event:
# https://lat.sk/2015/02/multiple-event-waiting-python-3/

# class WaitableEvent:
#     """
#         Provides an abstract object that can be used to resume select loops with
#         indefinite waits from another thread or process. This mimics the standard
#         threading.Event interface.
#     """
#     def __init__(self):
#         self._read_fd, self._write_fd = os.pipe()
#     def wait(self, timeout=None):
#         rfds, wfds, efds = select.select([self._read_fd], [], [], timeout)
#         return self._read_fd in rfds
#     def isSet(self):
#         return self.wait(0)
#     def clear(self):
#         if self.isSet():
#             os.read(self._read_fd, 1)
#     def set(self):
#         if not self.isSet():
#             os.write(self._write_fd, b'1')
#     def fileno(self):
#         """
#             Return the FD number of the read side of the pipe, allows this object to
#             be used with select.select().
#         """
#         return self._read_fd
#     def __del__(self):
#         os.close(self._read_fd)
#         os.close(self._write_fd)
#
# import selectors
#
# sel = selectors.DefaultSelector() # create selector
# event1 = WaitableEvent() # create event 1
# event2 = WaitableEvent() # create event 2
# sel.register(event1, selectors.EVENT_READ, "event 1")
# sel.register(event2, selectors.EVENT_READ, "event 2")
#
# events = sel.select(timeout=5)
# if not events:
#     print("Timeout after 5s")
# else:
#     for key, mask in events:
#         print(key.data)
