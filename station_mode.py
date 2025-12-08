import network
import socket
import time

WIFI_SSID = "WiFi_Name"
WIFI_PASS = "WiFi_Password"
UDP_IP = "0.0.0.0"  
UDP_PORT = 5005     # Must match the port your computer is sending to

def connect_wifi():
    wlan = network.WLAN(network.STA_IF) # Set to Station Mode (Client)
    wlan.active(True)
    
    if not wlan.isconnected():
        print('Connecting to network...')
        wlan.connect(WIFI_SSID, WIFI_PASS)
        
        max_wait = 10
        while not wlan.isconnected() and max_wait > 0:
            print(f"Waiting for connection... {max_wait}")
            time.sleep(1)
            max_wait -= 1
            
    if wlan.isconnected():
        print('Network connected!')
        print('Cyberbrick IP Config:', wlan.ifconfig())
        return wlan.ifconfig()[0]
    else:
        print('Failed to connect to WiFi.')
        return None

def start_udp_server(my_ip):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    try:
        sock.bind((UDP_IP, UDP_PORT))
        print(f"Listening for UDP on {my_ip}:{UDP_PORT}")
        
        while True:
            data, addr = sock.recvfrom(1024) 
            message = data.decode('utf-8')
            
            print(f"Received message: '{message}' from {addr}")
            
            reply = f"Acknowledged: {message}"
            sock.sendto(reply.encode('utf-8'), addr)
            
    except Exception as e:
        print(f"Error: {e}")
        sock.close()

my_ip_address = connect_wifi()

if my_ip_address:
    start_udp_server(my_ip_address)