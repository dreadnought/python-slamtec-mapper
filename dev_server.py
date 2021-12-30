#!/usr/bin/python3
import socket
import json
from pathlib import Path


def open_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = ('192.168.123.234', 1445)
    sock.bind(server_address)
    sock.listen(1)
    return sock


def handle_request(received, connection):
    received = received.decode("utf-8")
    received_json = json.loads(received)
    print("In:", received_json)
    dump_dir = "test_data"
    p = Path(f"{dump_dir}/{received_json['command']}-response.json")
    if not p.exists():
        print(p, "not found")
        return
    j = json.loads(p.read_text())
    j["request_id"] = received_json["request_id"]
    print("Out:", j)
    b = json.dumps(j).encode()
    connection.sendall(b + b"\r\n\r\n")


def handle_connection(connection):
    while True:
        received = connection.recv(1024)
        if len(received) == 0:
            print("connection end")
            break
        try:
            handle_request(received, connection)
        except ConnectionResetError:
            break

    connection.close()


sock = open_socket()
while True:
    try:
        connection, client_address = sock.accept()
    except KeyboardInterrupt:
        break
    print("connection from %s:%s" % client_address)
    handle_connection(connection)

sock.close()
