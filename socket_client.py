#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import selectors

HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
PORT = 65432  # Port to listen on (non-privileged ports are > 1023)

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.setblocking(False)

try:
    print(f'Connecting to server {HOST}....')
    client_socket.connect((HOST, PORT))
except BlockingIOError as e:
    print('Caught BlockingIOError')

sel = selectors.DefaultSelector()
sel.register(client_socket, selectors.EVENT_WRITE, 'SOCKET')

client_socket_ready_to_write = False
client_socket_ready_to_read = False

while not client_socket_ready_to_write:
    print(f'Waiting for socket read/write readiness....')
    for selector_key, event_mask in sel.select(1.0):
        if event_mask & selectors.EVENT_WRITE:
            print(f'Socket is ready to write')
            client_socket_ready_to_write = True

msg = 'Socket client says hello....\n'
byte_count = len(msg)
print(f'Sending {byte_count} bytes to server')
byte_count = client_socket.send(bytes(msg, 'UTF-8'))
print(f'Sent {byte_count} bytes to server')

sel.modify(client_socket, selectors.EVENT_READ, 'SOCKET')

msg_buffer = ''
keep_going = True

while keep_going:
    if client_socket_ready_to_read:
        try:
            # print(f'Reading bytes from server...')
            server_bytes = client_socket.recv(8)
            server_str = server_bytes.decode('utf8')
            # print(f'Read {len(server_bytes)} bytes from server')
            msg_buffer += server_str
            while '\n' in msg_buffer:
                linefeed_index = msg_buffer.index('\n')
                server_msg = msg_buffer[:linefeed_index]
                print(f'Received message: {server_msg}')
                msg_buffer = msg_buffer[linefeed_index + 1:]
                if server_msg == 'QUIT':
                    keep_going = False
        except BlockingIOError:
            client_socket_ready_to_read = False
    else:
        print(f'Waiting for socket read/write readiness....')
        events = sel.select(0.5)
        for selector_key, event_mask in events:
            if event_mask & selectors.EVENT_READ:
                print(f'Socket is ready to read')
                client_socket_ready_to_read = True

sel.unregister(client_socket)
sel.close()

client_socket.close()
