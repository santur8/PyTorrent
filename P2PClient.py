import socket
import argparse
import threading
import sys
import hashlib
import time
import logging
import os
import random

TRACKER_IP = "localhost"
LOCALHOST = "localhost"
LOCAL_FOLDER = ""
LOCAL_CHUNKS_FILE_PATH = ""
CLIENT_NAME = ""
TRANSFER_PORT = -1



#TODO: Implement P2PClient that connects to P2PTracker

#python3 P2PClient.py -folder folder1 -transfer_port 6000 -name tristan

def getNeededChunks(): # returning list of indicies
    file = open(LOCAL_CHUNKS_FILE_PATH, "r")
    index_list = []
    needed_chunks = []
    lines = file.readlines()
    if(len(lines) == 0):
        return []
    num_chunks = int(lines[len(lines)-1].split(",")[0])
    #print("num_chunks: " + str(num_chunks))
    for i in range(len(lines)-1):
        index_list.append(int(lines[i].split(",")[0]))
    #print("index_list: " + str(index_list))
    for i in range(num_chunks):
        shifted_index = i+1
        if (not shifted_index in index_list):
            needed_chunks.append(shifted_index)
    return needed_chunks

def getChunkFromPeer(index, peer, hash, tracker_socket): #index = int, peer = (ip(str), port(int))  returning void
    print("getting chunk " + str(index) + " from " + str(peer))
    peerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    connected = False
    while not connected:
        try:
            peerSocket.connect((peer[0], peer[1]))
            connected = True
        except:
            connected = False

    connectionClosed = False
    request_msg = "REQUEST_CHUNK," + str(index)
    peerSocket.send(request_msg.encode())
    request_msg = request_msg + "," + str(peer[0]) + "," + str(peer[1])
    logAction(request_msg)
    chunk_path = LOCAL_FOLDER + "/" + "chunk_" + str(index)
    chunk_file = open(chunk_path, "wb")
    while not connectionClosed:
        #print("receiving bytes from peer")
        return_msg = peerSocket.recv(1024)
        if not return_msg:
            connectionClosed = True
        else:
            chunk_file.write(return_msg)

    peerSocket.shutdown(socket.SHUT_RDWR)
    peerSocket.close()
    chunk_file.close()
    newChunkHash = findHashFile(chunk_path)
    
    if (newChunkHash != hash):
        #print("ERROR: HASH DOES NOT MATCH for index:" + str(index) + " from peer:" + str(peer))
        #print("newChunkHash: " + newChunkHash)
        #print("hash: " + hash)
        #sys.exit()
        os.remove(chunk_path)
        return None
    else:
        #update local chunks file
        #print("updating local chunks file")
        chunksFile = open(LOCAL_CHUNKS_FILE_PATH, "r+")
        
        lines = chunksFile.readlines()
        #print("lines: " + str(lines))
        lines.insert(0,str(index) + "," + "chunk_" + str(index) + "\n")
        lines[len(lines)-1] = str(int(lines[len(lines)-1].split(",")[0])) + "," + lines[len(lines)-1].split(",")[1]
        #logAction(str(lines))
        #print("lines2: " + str(lines))
        chunksFile.close()
        chunksFile = open(LOCAL_CHUNKS_FILE_PATH, "w")
        for line in lines:
            chunksFile.write(line)
        chunksFile.close()
        #sending update to tracker socket
        msg = "LOCAL_CHUNKS," + str(index) + "," + hash + "," + LOCALHOST + "," + str(TRANSFER_PORT)
        tracker_socket.send(msg.encode())
        logAction(msg)
    return

def findChunk(index, tracker_socket): #index = int, tracker_socket = socket.socket, returning ((ip(str), port(int)), hash(str))
    msg = "WHERE_CHUNK," + str(index)
    tracker_socket.send(msg.encode())
    logAction(msg)
    return_msg = tracker_socket.recv(1024).decode()
    #print("return message from tracker: " + return_msg)
    if (return_msg.startswith("CHUNK_LOCATION_UNKNOWN")):
        return (None, None)
    hash = return_msg.split(",")[2]
    peer_list = []
    split_msg = return_msg.split(",")
    split_msg.pop()
    for i in range(3, len(split_msg), 2):
        peer_list.append((split_msg[i], int(split_msg[i+1])))
    random_peer_index = random.randint(0, len(peer_list)-1)
    peer  = peer_list[random_peer_index]
    return (peer, hash)

def logAction(action): # action = str returning void
    file = open("logs.log", "a")
    action = CLIENT_NAME + "," + action.replace("127.0.0.1", "localhost")
    file.write(action + "\n")
    file.close()
    return

def haveAllChunks(): # returning bool
    file = open(LOCAL_CHUNKS_FILE_PATH, "r")
    lines = file.readlines()
    if(len(lines) == 0):
        return False
    numChunks = int(lines[len(lines)-1].split(",")[0])
    if (len(lines)-1 == numChunks):
        return True
    else:
        return False
    
def helpPeer():
    print("starting helper peer thread")
    p2p_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    p2p_socket.bind((LOCALHOST, TRANSFER_PORT))
    p2p_socket.listen()

    while True:
        # get new connection and request from peer
        conn_socket, addr = p2p_socket.accept()
        send = threading.Thread(target=sendToPeer, args=(conn_socket,))
        send.start()

def sendToPeer(conn_socket):
    request = conn_socket.recv(1024).decode()

    if (not request.startswith("REQUEST_CHUNK,")):
        #print("Closing help peer connection - BAD REQUEST")
        conn_socket.shutdown(socket.SHUT_RDWR)
        conn_socket.close()
        sys.exit()
    
    # send contents of file
    req_chunk = request.split(",")[1]
    #print("sending chunk " + req_chunk)
    filename = "chunk_" + req_chunk
    file =  open(LOCAL_FOLDER +"/"+ filename, mode='rb')
    while True:
        buff = file.read(1024)
        if not buff:
            break
        conn_socket.send(buff)
    file.close()

    # close socket
    #print("done sending chunk " + req_chunk)
    conn_socket.shutdown(socket.SHUT_RDWR)
    conn_socket.close()
    sys.exit()
        
def getChunk(tracker_socket): # tracker_socket = socket.socket returning void
    index_list = getNeededChunks()
    #print(index_list)
    next_index = index_list[0]
    peer, hash = findChunk(next_index, tracker_socket)
    if (peer is not None and hash is not None):
        getChunkFromPeer(next_index, peer, hash, tracker_socket)

def setupClient(): # returning tracker_socket
    tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tracker_socket.connect((TRACKER_IP, 5100))
    local_chunks_file = open(LOCAL_CHUNKS_FILE_PATH, "r")
    lines = local_chunks_file.readlines()
    lines.remove(lines[len(lines)-1]) #remove last line
    msg = ""
    for line in lines:
        chunk_index = line.split(",")[0]
        chunk_file_path = LOCAL_FOLDER + "/" + line.split(",")[1]
        hash = findHashFile(chunk_file_path)
        appended_msg = "LOCAL_CHUNKS," + chunk_index + "," + hash +","+ LOCALHOST + "," + str(TRANSFER_PORT)
        logAction(appended_msg)
        msg += appended_msg + "\n"
    tracker_socket.send(msg.encode())  
    time.sleep(1)
    return tracker_socket

def findHashFile(filename):
    """"This function returns the SHA-1 hash
    of the file passed into it"""
    # make a hash object
    filename = filename.replace("\n", "")
    h = hashlib.sha1()
    # open file for reading in binary mode
    with open(filename,'rb') as file:
        # loop till the end of the file
        chunk = 0
        while chunk != b'':
           # read only 1024 bytes at a time
           chunk = file.read(1024)
           h.update(chunk)
   # return the hex representation of digest
    return h.hexdigest()

def findHashString(string):
   """"This function returns the SHA-1 hash
   of the file passed into it"""
   # make a hash object
   h = hashlib.sha1()
   h.update(string.encode())
   # return the hex representation of digest
   return h.hexdigest()
    
    
    

if __name__ == "__main__":
    found_name = False
    found_port = False
    found_folder = False
    
    for arg in sys.argv:
        if (arg == "-folder") and len(sys.argv) > sys.argv.index(arg) + 1:
            LOCAL_FOLDER = sys.argv[sys.argv.index(arg) + 1]
            found_folder = True
        elif (arg == "-transfer_port") and len(sys.argv) > sys.argv.index(arg) + 1:
            TRANSFER_PORT = int(sys.argv[sys.argv.index(arg) + 1])
            found_port = True
        elif (arg == "-name") and len(sys.argv) > sys.argv.index(arg) + 1:
            CLIENT_NAME = sys.argv[sys.argv.index(arg) + 1]
            found_name = True

    if  found_folder and found_name and found_port:
        #print("NAME: "+ CLIENT_NAME + ", LOCAL FOLDER: " + LOCAL_FOLDER + ", TRANSFER PORT: " + str(TRANSFER_PORT))
        folder_contents = os.listdir(LOCAL_FOLDER)
        #print(folder_contents)
        if (not ("local_chunks.txt" in folder_contents)):
            #print("ERROR: local chunks file not found")
            sys.exit()
        LOCAL_CHUNKS_FILE_PATH = LOCAL_FOLDER + "/local_chunks.txt"
        got_all_chunks = False
        tracker_socket = setupClient()

        # start thread to help peers
        help_peer_thread = threading.Thread(target=helpPeer)
        help_peer_thread.start()
        print("thread started")

        while not got_all_chunks:
            # find what chunks we need
            got_all_chunks = haveAllChunks()
            if (not got_all_chunks):
                getChunk(tracker_socket)
        print("got all chunks")

            
    
                
                
