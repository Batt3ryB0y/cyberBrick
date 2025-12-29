import socket, struct
import numpy as np
import cv2
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # needed for 3D

UDP_IP = "0.0.0.0"
UDP_PORT = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

near, far = 10, 2500  # mm range for display
N = 5                # frames in rolling buffer
buffer = []

# --- prepare 3D plot ---
plt.ion()
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
X, Y = np.meshgrid(np.arange(8), np.arange(8))
surf = None

while True:
    data, addr = sock.recvfrom(128)  # 64 uint16 values
    if len(data) == 128:
        dist = struct.unpack("<64H", data)
        matrix = np.array(dist, dtype=np.float32).reshape((8, 8))

        # --- update rolling buffer ---
        buffer.append(matrix)
        if len(buffer) > N:
            buffer.pop(0)

        # --- smoothing ---
        smooth = np.mean(buffer, axis=0)

        # --- OpenCV visualization (colormap) ---
        norm = (np.clip(smooth - near, 0, far - near) / (far - near) * 255).astype(np.uint8)
        img = cv2.resize(norm, (400, 400), interpolation=cv2.INTER_NEAREST)
        img_color = cv2.applyColorMap(img, cv2.COLORMAP_JET)
        cv2.imshow("TOF 8x8 filtered", img_color)

        # --- 3D mesh plot ---
        ax.clear()
        surf = ax.plot_surface(X, Y, smooth, cmap='viridis')
        ax.set_zlim(near, far)
        ax.set_title("TOF 8x8 Surface")
        plt.pause(0.01)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

sock.close()
cv2.destroyAllWindows()
plt.ioff()
plt.show()
