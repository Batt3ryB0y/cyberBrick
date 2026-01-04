import socket
import json

ESP_IP = "192.168.4.1"  
ESP_PORT = 5005 
BUFFER_SIZE = 128  

def main():
    # UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Set a timeout so recvfrom() doesn't block forever
    sock.settimeout(1.0) 
    
    print(f"--- SERVO & FACTOR CONTROLLER ---")
    print(f"Target IP: {ESP_IP}")
    print(f"Target Port: {ESP_PORT}")
    print("Type an angle (0-180) and press Enter.\n'q' to quit.")
    print("---------------------------------")

    while True:
        user_input = input("Enter Angle: ")
        
        if user_input.lower() == 'q':
            break
            
        try:
            val = int(user_input)
            
            if 0 <= val <= 180:
                # angle command
                sock.sendto(user_input.encode(), (ESP_IP, ESP_PORT))
                
                try:
                    data, addr = sock.recvfrom(BUFFER_SIZE)
                    response_json = data.decode()
                    
                    # Parse the JSON response
                    response = json.loads(response_json)
                    factors = response.get('factors', [])
                    number = response.get('number', val)
                    
                    print(f"<- RESPONSE from {addr[0]}:")
                    print(f"<- Prime factors of {number} are: {factors}\n")
                    
                except socket.timeout:
                    print("-> Error: Timeout waiting for response from ESP.")
                except json.JSONDecodeError:
                    print("-> Error: Failed to parse JSON response from ESP.")
                except Exception as e:
                    print(f"-> Error during reception: {e}")
                    
            else:
                print("Please enter a number between 0 and 180.")
        
        except ValueError:
            print("Invalid number.")

if __name__ == "__main__":
    main()