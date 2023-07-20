import socket
import threading

LOCALHOST = "localhost"
HOSTPORT = 5100

client_list = []   # list of active server clients (socket, (IP, port))
check_list = {}	  # map of server clients to tuple (p2p_client, map of unverified hashes to chunks)
chunk_list = {}   # map of server clients (IP, port) to tuple (p2p_client, list of owned chunks with verified hashes)
hash_map = {}      # map of chunks to verified hashes

def log_action(action): # action = str returning void
    file = open("logs.log", "a")
    action = "P2PTracker," + action.replace("127.0.0.1", "localhost")
    file.write(action + "\n")
    file.close()
    return

# remove newly verified hash from client's check_list
# place matching entries in client's chunk_list
def clean_check_list(v_chunk, v_hash):
	for client in client_list:
		client_u_hashes = check_list.get(client)[1]
        
		if (v_hash not in client_u_hashes.keys()):
			continue
        
		chunk_num = client_u_hashes.get(v_hash)
		if (v_chunk != chunk_num):
			continue 

		# at this point, hash and chunk number match for client
		# remove entry in check_list and place in chunk_list
		del client_u_hashes[v_hash]

		p2p_addr = chunk_list.get(client)[0]
		client_v_chunks = chunk_list.get(client)[1]
		if (v_chunk not in client_v_chunks):
			client_v_chunks.append(v_chunk)
		chunk_list.update({client: (p2p_addr, client_v_chunks)})

# check if other clients have the same unverified hash 
def verify_hash(u_hash, u_chunk, curr_client):
    # check to see if two clients have the same hash
	for client in client_list:
		if (client == curr_client):
			continue 

		# get map of unverified hashes to chunks 
		hmap = check_list.get(client)[1]
		hlist = hmap.keys()
        
	    # see if u_hash matches any hashes in client's list
		if (u_hash in hlist):
			# check if chunk numbers match
			client_chunk_num = hmap.get(u_hash)
			if (client_chunk_num == u_chunk):
				# found a matching hash and chunk number between two clients
				# place it in verified list
				hash_map.update({u_chunk: u_hash})
				clean_check_list(u_chunk, u_hash)
				return

# command = "LOCAL_CHUNKS,<chunk_index>,<file_hash>,<IP_address>,<Port_number>\n..."
def handle_local_chunks(command, client_addr):
	commands = command.split("\n")
	if (command[-1] == '\n'):
		commands.pop() # remove empty string after last split

	for local_chunk in commands:
		data = local_chunk.split(",")
		chunk_num = int(data[1])
		hash = data[2]
		ip = data[3]
		port = int(data[4])
		p2p_addr = (ip, port)

		# update p2p_addr in chunk_list
		client_chunks = chunk_list.get(client_addr)[1]
		chunk_list.update({client_addr: (p2p_addr, client_chunks)})
        
		if (hash_map.get(chunk_num) == hash):
			# update client entry in chunk_list, hash already verified
			client_chunks = chunk_list.get(client_addr)[1]
			if chunk_num not in client_chunks:
				client_chunks.append(chunk_num)
			chunk_list.update({client_addr: (p2p_addr, client_chunks)})
		elif (chunk_num in hash_map.keys()):
			# chunk number has been verified, but client has wrong hash
			continue
		else:
			# hash not verified, place hash in check_list for client
			unverified = check_list.get(client_addr)[1]
			unverified.update({hash: chunk_num})
			check_list.update({client_addr: (p2p_addr, unverified)})
			
			# attempt to verify hash with other clients
			verify_hash(hash, chunk_num, client_addr)

# return info
# info = "GET_CHUNK_FROM,<chunk_index>,<file_hash>,<IP_address1>,<Port_number1>,<IP_address2>,<Port_number2>,..."
# command = "WHERE_CHUNK,<chunk_index>"
def handle_where_chunk(command):
	req_chunk = int(command.split(",")[1])
    
	# if chunk not verified, can't get valid location
	if req_chunk not in hash_map.keys():
		return "CHUNK_LOCATION_UNKNOWN," + str(req_chunk)

	info = "GET_CHUNK_FROM," + str(req_chunk) + ","
	info += hash_map.get(req_chunk) + ","

	found = False
	for client in client_list:
		p2p_info = chunk_list.get(client)
		p2p_addr = p2p_info[0]
		client_chunks = p2p_info[1]
		if (req_chunk in client_chunks):
			# append client to info
			found = True
			info += (p2p_addr[0] + ",") # IP addr
			info += (str(p2p_addr[1]) + ",") # port
	
	if not found:
		return "CHUNK_LOCATION_UNKNOWN," + str(req_chunk)
	return info

# handle client interactions with server
def client_handle(connSocket, client_addr):
	# create client entries
	client_list.append(client_addr)
	chunk_list.update({client_addr: (("null", 0), [])})
	check_list.update({client_addr: (("null", 0), {})})
	
	while True:
		# wait for command
		command = connSocket.recv(1024).decode()

		# handle different commands
		if command.startswith("LOCAL_CHUNKS,"):
			handle_local_chunks(command, client_addr)
		elif command.startswith("WHERE_CHUNK,"):
			info = handle_where_chunk(command)
			connSocket.send(info.encode())
			if (info[-1] == ","):
				info = info[0:-2]
			log_action(info)
		else:
		    continue

if __name__ == "__main__":
	server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server_socket.bind((LOCALHOST, HOSTPORT))
	server_socket.listen()
	
	while True:
		# accept incoming connections and wait for messages
		conn_socket, addr = server_socket.accept()
		recv_thread = threading.Thread(target=client_handle, args=(conn_socket, addr,))
		recv_thread.start()
