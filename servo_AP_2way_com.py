import uasyncio
import network
import ulogger
import socket
import time
import ujson
from machine import Pin, PWM
import rc_module

SERVO_PIN = 3 
UDP_PORT = 5005
AP_SSID = "Cyberbrick_AP"
AP_KEY = "12345678"

DUTY_MIN = 26   # 0 deg
DUTY_MAX = 128  # 180 deg

def angle_to_duty(angle):
    """Converts a 0-180 degree angle to the servo PWM duty cycle."""
    if angle < 0: angle = 0
    if angle > 180: angle = 180
    duty = DUTY_MIN + (angle * (DUTY_MAX - DUTY_MIN) / 180)
    return int(duty)

def prime_factors(n):

    factors = []
    
    if n <= 1:
        return []

    d = 2
    temp = n
    while d * d <= temp:
        if temp % d == 0:
            factors.append(d)
            temp //= d
        else:
            d += 1
    if temp > 1:
        factors.append(temp)
    return factors

# --- ASYNCHRONOUS TASKS ---

async def servo_udp_task():
    logger = ulogger.Logger()
    logger.info(f"[SERVO] Listener started on Pin {SERVO_PIN}")
    
    # Setup 
    try:
        servo = PWM(Pin(SERVO_PIN), freq=50)
        servo.duty(angle_to_duty(90))  # Center the servo 
    except Exception as e:
        logger.error(f"[SERVO] PWM Fail: {e}")
        return

    # Setup Socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', UDP_PORT))
    sock.setblocking(False)  
    

    while True:
        try:
            # recvfrom - receive data and sender address from socket
            data, addr = sock.recvfrom(64)
            msg = data.decode().strip()
            
            angle = None
            try:
                angle = int(msg)
                
                # 1. Control Servo
                if 0 <= angle <= 180:
                    servo.duty(angle_to_duty(angle))
                    logger.info(f"[SERVO] Set angle to {angle}")
                
                # 2. Calculate and Send Prime Factors Back
                factors = prime_factors(angle)
                
                # Prepare JSON response
                response_data = {'factors': factors, 'number': angle}
                response_json = ujson.dumps(response_data)
                
                # Send the response back to the sender's address (addr)
                sock.sendto(response_json.encode(), addr)
                logger.info(f"[PRIME] Sent factors for {angle}: {factors}")
                
            except ValueError:
                logger.warn(f"[RX] Received non-integer data: {msg}")
                pass
                
        except OSError as e:
            if e.args[0] == 11:  # errno 11 is EAGAIN/EWOULDBLOCK
                pass
            else:
                logger.error(f"[SOCKET] Error: {e}")
                
        # Yield to allow other tasks to run
        await uasyncio.sleep_ms(20)

async def run_master_mode():
    logger = ulogger.Logger()
    logger.info("[RUNNER] STARTING...")

    try:
        # Init hw
        if rc_module.rc_master_init() is False:
            logger.error("Hardware Init Failed")
            return

        # Start AP
        ap = network.WLAN(network.AP_IF)
        ap.config(ssid=AP_SSID, key=AP_KEY, security=network.AUTH_WPA2_PSK)
        ap.active(True)
        
        while not ap.active():
            await uasyncio.sleep_ms(100)
            
        logger.info(f"[WIFI] AP Ready: {ap.ifconfig()[0]}")

        # Servo udp task
        async def rc_task():
            while True:
                rc_module.file_transfer()
                await uasyncio.sleep(1)

        # Run everything
        await uasyncio.gather(rc_task(), servo_udp_task())

    except uasyncio.CancelledError:
        logger.info("[SYSTEM] Tasks Cancelled")
    except Exception as e:
        logger.error(f"[SYSTEM] Crash: {e}")
    finally:
        pass


print("!!! PRESS CTRL+C NOW TO STOP !!!")
time.sleep(1)
print("4...")
time.sleep(1)
print("3...")
time.sleep(1)
print("2...")
time.sleep(1)
print("1...")
time.sleep(1)
print("--- LAUNCHING ---")

try:
    uasyncio.run(run_master_mode())
except KeyboardInterrupt:
    print("\n[USER] Stopped by Ctrl+C")
finally:
    uasyncio.new_event_loop()