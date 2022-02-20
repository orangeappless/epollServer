#!/usr/bin/python


import sys
from socket import *
import threading
from datetime import datetime
import time
import json


def export_client_stats(stats):
    with open("client_stats.json", "a") as file:
        json.dump(stats, file, indent=2)


def client_conn():
    server_host = "192.168.1.78"
    server_port = 8000

    sock = socket(AF_INET, SOCK_STREAM)
    #print(f"Connecting to {server_host}:{server_port}...")
    try:
        sock.connect((server_host, server_port))
    except:
        print("Cannot connect to server")
        return

    return sock


def send_data(sock, data):
    current_time = datetime.now()
    current_time_formatted = current_time.strftime("%Y-%m-%d %H:%M:%S:%f")[:-3]

    sock.send(f"{current_time_formatted} {data}".encode("utf-8"))


def receive_response(sock):
    current_time = datetime.now()
    current_time_formatted = current_time.strftime("%Y-%m-%d %H:%M:%S:%f")[:-3]

    # Receive response from server
    response = sock.recv(1024)
    response_msg = response.decode("utf-8")
    print(f"Server response [{current_time_formatted}]: {response_msg}")


def create_client(client_name, send_reps):
    c_sock = client_conn()

    msg = "Hello world"

    client_stats = {
        "client_id": client_name,
        "reqs_made": 0, 
        "total_sent": 0,
        "response_time": []
    }

    for x in range(1, send_reps+1):
        # send_data(c_sock, msg)
        # receive_response(c_sock)

        # TODO: TEST BELOW
        current_time = datetime.now()
        current_time_formatted = current_time.strftime("%Y-%m-%d %H:%M:%S:%f")[:-3]

        payload = f"{current_time_formatted}: {msg}"
        payload_length = len(payload)

        t1 = time.perf_counter()
        c_sock.send(payload.encode("utf-8"))

        client_stats["reqs_made"] += 1
        client_stats["total_sent"] += payload_length   

        # Receive response from server
        response = c_sock.recv(1024)
        t2 = time.perf_counter()

        response_time = f"%.5f" % ((t2-t1)*1000.0)
        client_stats["response_time"].append(response_time)

    c_sock.close()

    export_client_stats(client_stats)


def main():
    if len(sys.argv) > 1:
        if sys.argv[1].isdigit() and sys.argv[2].isdigit():
            num_msgs = int(sys.argv[2])
            client_num = 1

            # Repeated client spawns
            if sys.argv[1] == "0":
                while True:
                    threading.Thread(target=create_client, args=(client_num, num_msgs,),).start()
                    print(f"Client #{client_num} created")
                    client_num += 1

            # Specific number of clients
            else:
                num_clients = int(sys.argv[1])

                for x in range(client_num, num_clients+1):
                    threading.Thread(target=create_client, args=(x, num_msgs,),).start()
                    #print(f"Client #{x} created")
        else:
            print("Invalid args: Please provide a number-value (e.g., 1, 2, 3...)")
            print("Usage: python spawn_clients.py [num_clients] [num_msgs]")
            exit(0)
    else:
        print("Usage: python spawn_clients.py [num_clients] [num_msgs]")
        exit(0)


if __name__ == "__main__":
    main()
