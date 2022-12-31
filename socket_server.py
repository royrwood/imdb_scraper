#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import select
import time

HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 65432  # Port to listen on (non-privileged ports are > 1023)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_listen_socket:
    server_listen_socket.bind((HOST, PORT))

    print(f'Configuring listen socket as non-blocking...')
    server_listen_socket.setblocking(False)

    print(f'Listening on socket...')
    server_listen_socket.listen()

    while True:
        print(f'Calling select on listen socket...')
        readable, writeable, exceptable = select.select([server_listen_socket], [server_listen_socket], [], 1.0)
        if readable or writeable:
            break

    print(f'Accepting connection...')
    conn, addr = server_listen_socket.accept()
    conn.setblocking(False)

    try:
        print(f'Servicing connection...')
        with conn:
            print(f'Connected by {addr}')
            msg_count = 0
            while True:
                print(f'Calling select...')
                readable, writeable, exceptable = select.select([conn], [conn], [], 5.0)

                if readable:
                    try:
                        print(f'Socket is readable; reading data...')
                        data = conn.recv(1024)

                        if not data:
                            print(f'Read no data; connection closed; exiting...')
                            break

                        print(f'Read {len(data)} bytes of data: {data}')
                    except BlockingIOError:
                        print(f'Caught BlockingIOError')

                if writeable:
                    print(f'Writing msg #{msg_count}')
                    msg_bytes = f'{msg_count=}\n'.encode('utf8')
                    conn.sendall(msg_bytes)
                    msg_count += 1
                    time.sleep(3.0)

    except BrokenPipeError:
        print(f'Caught BrokenPipeError; exiting...')