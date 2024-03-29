#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import socket
import select
import sys
import time

HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 65432  # Port to listen on (non-privileged ports are > 1023)


def main(argv):
    if argv:
        host_ip = argv[0]
    else:
        host_ip = HOST

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_listen_socket:
        server_listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_listen_socket.bind((host_ip, PORT))

        logging.info(f'Configuring listen socket as non-blocking...')
        server_listen_socket.setblocking(False)

        logging.info(f'Listening on socket...')
        server_listen_socket.listen()

        while True:
            while True:
                logging.info(f'Calling select on listen socket...')
                readable, writeable, exceptable = select.select([server_listen_socket], [server_listen_socket], [], 1.0)
                if readable or writeable:
                    break

            # logging.info(f'Sleeping before accepting connection...')
            # time.sleep(5)

            logging.info(f'')
            logging.info(f'')
            logging.info(f'Accepting connection...')
            conn, addr = server_listen_socket.accept()
            conn.setblocking(False)
            logging.info(f'Connected by {addr}')

            try:
                logging.info(f'Servicing connection...')
                with conn:
                    server_msg_count = 0
                    client_msg_buffer = ''

                    while True:
                        logging.info(f'Calling select...')
                        readable, writeable, exceptable = select.select([conn], [conn], [], 5.0)

                        if readable:
                            try:
                                logging.info(f'Socket is readable; reading data...')
                                client_bytes = conn.recv(1024)

                                if not client_bytes:
                                    logging.info(f'Read no data; connection closed; exiting...')
                                    break

                                client_str = client_bytes.decode('utf8')
                                client_msg_buffer += client_str
                                while '\n' in client_msg_buffer:
                                    linefeed_index = client_msg_buffer.index('\n')
                                    client_msg = client_msg_buffer[:linefeed_index]
                                    logging.info(f'Received message: {client_msg}')
                                    client_msg_buffer = client_msg_buffer[linefeed_index + 1:]
                            except BlockingIOError:
                                logging.info(f'Caught BlockingIOError')

                        if writeable:
                            logging.info(f'Writing msg #{server_msg_count}')
                            msg_bytes = f'{server_msg_count=}\n'.encode('utf8')
                            conn.sendall(msg_bytes)
                            server_msg_count += 1
                            time.sleep(3.0)

            except BrokenPipeError:
                logging.info(f'Caught BrokenPipeError; exiting...')


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s [%(levelname)s] %(funcName)s:%(lineno)d: %(message)s', level=logging.INFO)

    main(sys.argv[1:])