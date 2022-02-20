#!/usr/bin/python


from socket import *
import select
import queue
import json


def export_server_stats(client_addr, num_reqs, total_data_received):
    server_stats = {
        "client_id": client_addr,
        "num_reqs": num_reqs,
        "total_received": total_data_received
    }

    with open("server_stats.json", "a") as file:
        json.dump(server_stats, file, indent=2)


def create_socket():
    host = ""
    port = 8000  

    sock = socket(AF_INET, SOCK_STREAM)
    sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

    sock.bind((host, port))
    sock.listen()
    sock.setblocking(0)
    print(f"Server listening on port {port}...")

    return sock


def init_connection(server_socket, epoll_obj, conns_list, client_addrs_list, messages_list, client_reqs_list, from_client_list, to_client_list):
    conn, addr = server_socket.accept()
    conn.setblocking(0)
    
    print(f"Client connected: {addr}")

    client_fd = conn.fileno()
    epoll_obj.register(client_fd, select.EPOLLIN)

    # Add client socket info to appropriate dicts
    conns_list[client_fd] = conn
    client_addrs_list[client_fd] = addr
    client_reqs_list[client_fd] = 0
    from_client_list[client_fd] = 0
    to_client_list[client_fd] = 0

    # Add data to message queue
    messages_list[client_fd] = queue.Queue()
    print(f"Current number of connections: {len(client_addrs_list)}")


def handle_data(epoll_obj, fd, conns_list, client_addrs_list, messages_list, client_reqs_list, from_client_list, to_client_list):
    data = conns_list[fd].recv(1024)

    # Handle data and add to queue
    if data:
        client_reqs_list[fd] += 1
        # print(f"Total requests from {client_addrs_list[fd]}: {client_reqs_list[fd]}")

        messages_list[fd].put(data)

        # Process data length
        data_str = data.decode("utf-8")
        data_length = len(data_str)
        total_length = from_client_list[fd] + data_length
        from_client_list[fd] = total_length

        # print(f"Total data from {client_addrs_list[fd]}: {from_client_list[fd]}")
        # print(f"{client_addrs_list[fd]} sent: {data.decode('utf-8')}")
        epoll_obj.modify(fd, select.EPOLLOUT)

    # No data, client disconnect/close
    elif data == "" or data == b"":
        print(f"Client disconnected or closed: {client_addrs_list[fd]}")
        export_server_stats(client_addrs_list[fd], client_reqs_list[fd], from_client_list[fd])

        epoll_obj.unregister(fd)
        conns_list[fd].close()
        del conns_list[fd], client_addrs_list[fd], messages_list[fd], client_reqs_list[fd], from_client_list[fd], to_client_list[fd]

        print(f"Current number of connections: {len(client_addrs_list)}")


def send_response(epoll_obj, fd, conns_list, messages_list, to_client_list):
    try:
        msg = messages_list[fd].get_nowait()
    except queue.Empty:
        epoll_obj.modify(fd, select.EPOLLIN)
        pass
    else:
        msg_str = msg.decode("utf-8")

        # Process data length
        data_length = len(msg_str)
        total_length = to_client_list[fd] + data_length
        to_client_list[fd] = total_length

        #print(f"Echoing to client: {msg_str}")
        conns_list[fd].send(msg)
        # print(f"Total data to {conns_list[fd].getpeername()}: {to_client_list[fd]}")


def main():
    serv_sock = create_socket()

    # epoll wrapping
    epoll = select.epoll()
    epoll.register(serv_sock.fileno(), select.EPOLLIN)

    # Structures to store info
    server_fd = serv_sock.fileno()
    connections = {server_fd:serv_sock,}
    client_addrs = {}
    messages = {}

    # Tracking data from/to client
    total_reqs = {}
    data_from_client = {}
    data_to_client = {}

    while True:
        events = epoll.poll(1)

        for fileno, event in events:
            sock_fd = connections[fileno]

            # Process client connections if fd is server socket's
            if sock_fd == serv_sock:
                init_connection(serv_sock, epoll, connections, client_addrs, messages, total_reqs, data_from_client, data_to_client)

            # Receive request/read client data
            elif event & select.EPOLLIN:
                handle_data(epoll, fileno, connections, client_addrs, messages, total_reqs, data_from_client, data_to_client)

            # Send response to client
            elif event & select.EPOLLOUT:
                send_response(epoll, fileno, connections, messages, data_to_client)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt as e:
        print("\nServer shutting down...")
        exit(0)
