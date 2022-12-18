#!/usr/bin/python

import sys
import os
import time
import selectors


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
    sel.register(r_file, selectors.EVENT_READ, None)

    while True:
        print('PARENT: Waiting for read on r_file')
        events = sel.select(0.5)
        if events:
            print('PARENT: Reading r_file')
            text = r_file.read()
            print(f'PARENT: Read "{text}"')
            break

    sel.unregister(r_file)
    sel.close()

    sys.exit(0)
else:
    print('CHILD: Closing r_fd')
    os.close(r_fd)

    print('CHILD: Opening w_file')
    w_file = os.fdopen(w_fd, 'w')
    print('CHILD: Sleeping')
    time.sleep(3)
    print('CHILD: Writing w_file')
    w_file.write('CHILD SAYS HELLO')
    sys.exit(0)
