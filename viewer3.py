import socket
import struct
import numpy as np
import cv2
import time

# -------------------- CONFIG --------------------
UDP_IP = "0.0.0.0"
UDP_PORT = 5005

# Visualization Ranges (in mm)
NEAR_MM = 100         # Objects closer than this are RED (Hot)
FAR_MM = 2000         # Objects further than this are BLUE (Cold)

FRAME_SIZE = 8        # 8x8 TOF
SMOOTH_ALPHA = 0.3    # Lower = smoother but more lag (0.0 to 1.0)
DISPLAY_SIZE = 600    # Window size in pixels

# -------------------- SETUP SOCKET --------------------
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# Allow rebinding immediately if script restarts
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind((UDP_IP, UDP_PORT))
sock.setblocking(False)

print(f"Listening on port {UDP_PORT}...")

# -------------------- INITIALIZATION --------------------
# Initialize 'smooth' grid to FAR_MM so the screen starts empty (blue)
smooth_grid = np.full((FRAME_SIZE, FRAME_SIZE), FAR_MM, dtype=np.float32)

try:
    while True:
        data_found = False
        
        # --- 1. DRAIN THE SOCKET ---
        # Loop until error to ensure we get the absolute LATEST packet
        try:
            while True:
                data, addr = sock.recvfrom(4096) # Request more than 128 to be safe
                if len(data) == 128:
                    # We have a valid packet
                    raw = struct.unpack("<64H", data)
                    new_grid = np.array(raw, dtype=np.float32).reshape((FRAME_SIZE, FRAME_SIZE))
                    
                    # Exponential smoothing
                    smooth_grid = (SMOOTH_ALPHA * new_grid) + ((1 - SMOOTH_ALPHA) * smooth_grid)
                    data_found = True
        except BlockingIOError:
            pass # Buffer is empty, move on
        
        # --- 2. VISUALIZATION ---
        # Update visualization even if no new data came (to keep window responsive)
        if data_found:
             # Normalize: Clip to range
            clipped = np.clip(smooth_grid, NEAR_MM, FAR_MM)
            
            # Invert: (FAR - val) makes Close objects High Value
            norm = (FAR_MM - clipped) / (FAR_MM - NEAR_MM) * 255
            frame_u8 = norm.astype(np.uint8)

            # Resize (Nearest Neighbor preserves the 'pixel' look)
            img_big = cv2.resize(frame_u8, (DISPLAY_SIZE, DISPLAY_SIZE), interpolation=cv2.INTER_NEAREST)
            
            # Apply Heatmap (JET: Blue=Cold/Low, Red=Hot/High)
            img_color = cv2.applyColorMap(img_big, cv2.COLORMAP_JET)
            cv2.imshow("TOF Stream", img_color)
        
        # --- 3. INPUT HANDLING ---
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        # Sleep slightly to prevent 100% CPU usage
        time.sleep(0.001)

finally:
    sock.close()
    cv2.destroyAllWindows()
    print("Socket closed.")