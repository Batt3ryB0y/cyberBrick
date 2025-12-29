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



BROADCAST_IP = "192.168.4.255"
PORT = 5005

ZONE_COUNT = 64                  # 8x8
TOF_RESOLUTION = RESOLUTION_8X8
TOF_FREQ_HZ = 20             # ranging frequency



class Clock():  # simple time logger
    def __init__(self):
        self.start = time.time()

    def __call__(self) -> str:
        return "%d" % (time.time() - self.start)


async def main():

    # RC init
    if rc_module.rc_slave_init() is False:
        return

    # wifi AP
    ap = network.WLAN(network.AP_IF)
    ap.config(
        ssid="Cyberbrick_AP",
        key="12345678",
        security=network.AUTH_WPA2_PSK
    )

    # NOTE: Blocking here (one time init)
    i2c = SoftI2C(
        sda=Pin(3),
        scl=Pin(2),
        freq=400_000
    )

    tof = VL53L5CXMP(i2c)
    tof.init()
    tof.resolution = TOF_RESOLUTION
    tof.ranging_freq = TOF_FREQ_HZ
    tof.target_order = TARGET_ORDER_CLOSEST
    tof.start_ranging({DATA_DISTANCE_MM})


    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    broadcast_addr = (BROADCAST_IP, PORT)

    # 64 zones * uint16 = 128 bytes
    buf = bytearray(ZONE_COUNT * 2)
    pack_fmt = f"<{ZONE_COUNT}H"

    while True:

        if tof.check_data_ready():
            res = tof.get_ranging_data()

            pack_into(pack_fmt, buf, 0, *res.distance_mm)

            try:
                sock.sendto(buf, broadcast_addr)
            except OSError:
                pass

        await asyncio.sleep_ms(1000 // TOF_FREQ_HZ) # basically the only yield (asincio.sleep)

if __name__ == "__main__":

    rst_c = machine.reset_cause()

    log_clock = Clock() # time logger

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

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrupted")
    finally:
        asyncio.new_event_loop()
