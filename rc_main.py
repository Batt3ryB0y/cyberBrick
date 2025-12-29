import sys
import machine
import time
import ulogger
import uasyncio as asyncio

sys.path.append("/app")
if '.frozen' in sys.path:
    sys.path.remove('.frozen')
    sys.path.append('.frozen')

import socket
import struct
from struct import pack_into
import network

from machine import SoftI2C, Pin
from vl53l5cx.mp import VL53L5CXMP
from vl53l5cx import RESOLUTION_8X8, DATA_DISTANCE_MM, TARGET_ORDER_CLOSEST

import rc_module

BROADCAST_IP = "192.168.4.255"
PORT = 5005
TOF_RESOLUTION = RESOLUTION_8X8

async def main():
    
    if rc_module.rc_slave_init() is False:
        return
    
    # WiFi AP
    ap = network.WLAN(network.AP_IF)
    ap.config(ssid="Cyberbrick_AP", key="12345678", security=network.AUTH_WPA2_PSK)
    
    # TOF sensor init
    i2c = SoftI2C(sda=Pin(3), scl=Pin(2), freq=400_000)
    tof = VL53L5CXMP(i2c)
    tof.init()
    tof.resolution = TOF_RESOLUTION
    tof.ranging_freq = 10
    tof.target_order = TARGET_ORDER_CLOSEST
    tof.start_ranging({DATA_DISTANCE_MM})

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    broadcast_addr = (BROADCAST_IP, PORT)

    dist = [0] * TOF_RESOLUTION
    buf = bytearray(TOF_RESOLUTION<<1)
    pack_fmt = f"<{TOF_RESOLUTION}H"

    while True:
        
        if tof.check_data_ready():
            res = tof.get_ranging_data()
            d_mm = res.distance_mm
            for i in range(TOF_RESOLUTION):
                dist[i] = d_mm[i]
            pack_into(pack_fmt, buf, 0, *dist)
            
            
        
        try:
            sock.sendto(buf, broadcast_addr)
        except OSError:
            pass

        await asyncio.sleep_ms(50)

class Clock(ulogger.BaseClock):
    def __init__(self):
        self.start = time.time()

    def __call__(self) -> str:
        inv = time.time() - self.start
        return '%d' % (inv)


if __name__ == "__main__":
    rst_c = machine.reset_cause()
    log_clock = Clock()

    log_handler_to_term = ulogger.Handler(
        level=ulogger.INFO,
        colorful=True,
        fmt="&(time)%-&(level)%-&(msg)%",
        clock=log_clock,
        direction=ulogger.TO_TERM,
    )

    log_handler_to_file = ulogger.Handler(
        level=ulogger.INFO,
        fmt="&(time)%-&(level)%-&(msg)%",
        clock=log_clock,
        direction=ulogger.TO_FILE,
        file_name="./log/logging",
        index_file_name="./log/log_index.txt",
        max_file_size=10240
    )

    logger = ulogger.Logger(name=__name__,
                            handlers=(
                                log_handler_to_term,
                                log_handler_to_file))

    rc2str = {
        getattr(machine, i): i
        for i in ('PWRON_RESET',
                  'HARD_RESET',
                  'WDT_RESET',
                  'DEEPSLEEP_RESET',
                  'SOFT_RESET')
    }

    logger.info("[MAIN]{}".format(rc2str.get(rst_c, str(rst_c))))

    
    asyncio.run(main())

