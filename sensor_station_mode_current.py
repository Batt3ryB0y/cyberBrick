import sys
import machine
import time
import ulogger
import uasyncio as asyncio
import socket
import network

from machine import SoftI2C, Pin
from struct import pack_into

from vl53l5cx.mp import VL53L5CXMP
from vl53l5cx import RESOLUTION_8X8, DATA_DISTANCE_MM, TARGET_ORDER_CLOSEST

import rc_module


# -------------------- CONSTANTS --------------------

BROADCAST_IP = "192.168.100.255"
PORT = 5005

ZONE_COUNT = 64                  # 8x8
TOF_RESOLUTION = RESOLUTION_8X8
TOF_FREQ_HZ = 20                 # stable & realistic

WIFI_SSID = "HUAWEI-A94j-2G"
WIFI_PASS = "uc5RR3k3"
wlan = network.WLAN(network.STA_IF)
wlan.active(True)


def connect_wifi(timeout=30):
    """
    Connect to WiFi in station mode.
    Returns the IP address if successful, None otherwise.
    """
    print("Activating WiFi...")
    
    
    if not wlan.isconnected():
        print(f"Connecting to {WIFI_SSID}...")
        wlan.disconnect()
        wlan.connect(WIFI_SSID, WIFI_PASS)

        wait = timeout
        while not wlan.isconnected() and wait > 0:
            print(f"Waiting for connection... {wait}")
            time.sleep(1)
            wait -= 1

    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print(f"WiFi connected! IP: {ip}")
        # extra delay to ensure DHCP routing is ready
        time.sleep(1)
        return ip
    else:
        print("Failed to connect to WiFi.")
        return None



# -------------------- LOGGER CLOCK --------------------

class Clock():
    def __init__(self):
        self.start = time.time()

    def __call__(self) -> str:
        return "%d" % (time.time() - self.start)


# -------------------- MAIN ASYNC TASK --------------------

async def main():

    # RC init
    print("here")
    if rc_module.rc_slave_init() is False:
        return
    print("there")
    
    # -------------------- TOF SENSOR INIT --------------------
    # NOTE: Blocking here is OK (one-time init)
    i2c = SoftI2C(
        sda=Pin(3),
        scl=Pin(2),
        freq=400_000
    )
    print("TOF obj")
    tof = VL53L5CXMP(i2c)
    print("TOF init")
    tof.init()
    print("TOF init done")
    tof.resolution = TOF_RESOLUTION
    tof.ranging_freq = TOF_FREQ_HZ
    tof.target_order = TARGET_ORDER_CLOSEST
    tof.start_ranging({DATA_DISTANCE_MM})

    # -------------------- UDP SOCKET --------------------
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)
    sock.bind(("0.0.0.0",0))
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    broadcast_addr = (BROADCAST_IP, PORT)

    # -------------------- BUFFERS --------------------
    # 64 zones * uint16 = 128 bytes
    buf = bytearray(ZONE_COUNT * 2)
    pack_fmt = f"<{ZONE_COUNT}H"

    # -------------------- MAIN LOOP --------------------
    while True:

        # ===== CRITICAL SECTION (NO await here) =====
        if tof.check_data_ready():
            res = tof.get_ranging_data()

            # Pack directly into preallocated buffer
            pack_into(pack_fmt, buf, 0, *res.distance_mm)

            # Send only when new data is available
            try:
                sock.sendto(buf, broadcast_addr)
            except OSError:
                # Network buffer full / WiFi busy
                pass
        # ===== END CRITICAL SECTION =====
        await asyncio.sleep_ms(10)
        

        # Yield safely (gives time to WiFi + asyncio)
#        await asyncio.sleep_ms(1000 // TOF_FREQ_HZ)


# -------------------- ENTRY POINT --------------------

if __name__ == "__main__":

    rst_c = machine.reset_cause()

    log_clock = Clock()

    logger = ulogger.Logger(
        name=__name__,
        handlers=(
            ulogger.Handler(
                level=ulogger.INFO,
                colorful=True,
                fmt="&(time)%-&(level)%-&(msg)%",
                clock=log_clock,
                direction=ulogger.TO_TERM,
            ),
        ),
    )

    rc2str = {
        getattr(machine, i): i
        for i in (
            "PWRON_RESET",
            "HARD_RESET",
            "WDT_RESET",
            "DEEPSLEEP_RESET",
            "SOFT_RESET",
        )
        if hasattr(machine, i)
    }

    logger.info(
        "[MAIN] Reset cause: {}".format(
            rc2str.get(rst_c, str(rst_c))
        )
    )
    ip = connect_wifi()
    if ip is None:
        raise RuntimeError("Cannot continue without WiFi")
    
    print("Starting main program...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrupted")
    finally:
        asyncio.new_event_loop()

