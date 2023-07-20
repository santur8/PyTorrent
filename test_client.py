import socket
import argparse
import threading
import sys
import hashlib
import time
import logging
import time

def test_where_chunk(sock):
    time.sleep(1)
    sock.send("WHERE_CHUNK,2".encode())
    response = sock.recv(1000).decode()
    print(response)

def test_local_chunks(sock):
    time.sleep(1)
    msg = "LOCAL_CHUNKS,1,hash3,127.0.0.1,6960\nLOCAL_CHUNKS,2,hash4,127.0.0.1,6960"
    sock.send(msg.encode())

if __name__ == "__main__":
    test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    test_socket.connect(("127.0.0.1", 5100))

    test_where_chunk(test_socket)
    #test_local_chunks(test_socket)


