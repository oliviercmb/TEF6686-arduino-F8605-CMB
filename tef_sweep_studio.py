"""FM spectrum scan display — TEF6686 F8605
Serial runs in a background thread; matplotlib animates from the main thread.
"""
import serial
import time
import sys
import threading
import queue
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.animation import FuncAnimation

PORT  = "COM1"
BAUD  = 115200
LIVE  = True   # False = single scan, True = live refresh loop

SCAN_START = 87500   # 87.5 MHz (kHz)
SCAN_END   = 108000  # 108.0 MHz (kHz)
SCAN_STEP  = 100     # 100 kHz step

# ── serial helpers ────────────────────────────────────────────────────────────

def handshake(ser):
    time.sleep(2.0)
    ser.reset_input_buffer()
    ser.write(b"x\n")
    resp = ser.read_until(b"OK\n", size=64)
    if b"OK" not in resp:
        sys.exit("No OK from device — check port and baud rate")
    time.sleep(0.1)

def setup_scan(ser):
    for cmd in [
        f"Sa{SCAN_START}\n".encode(),
        f"Sb{SCAN_END}\n".encode(),
        f"Sc{SCAN_STEP}\n".encode(),
        b"Sf0\n",
    ]:
        ser.write(cmd)
        time.sleep(0.05)

def parse_scan(line: bytes) -> dict:
    result = {}
    line = line.strip()
    if not line.startswith(b"U"):
        return result
    for entry in line[1:].split(b","):
        try:
            f, r = entry.split(b"=")
            result[int(f) / 1000] = int(r)   # kHz -> MHz
        except ValueError:
            pass
    return result

def serial_worker(ser, data_queue: queue.Queue, stop_event: threading.Event):
    pass_n = 0
    while not stop_event.is_set():
        ser.reset_input_buffer()
        ser.write(b"Ss\n")
        t0 = time.perf_counter()
        line = ser.read_until(b"\n", size=8192)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        data = parse_scan(line)
        if data:
            pass_n += 1
            data_queue.put((data, elapsed_ms, pass_n))
        if not LIVE:
            stop_event.set()

# ── plot ──────────────────────────────────────────────────────────────────────

def build_plot():
    fig, ax = plt.subplots(figsize=(14, 5))
    fig.patch.set_facecolor("#0d0d0d")
    ax.set_facecolor("#0d0d0d")
    ax.set_xlabel("Frequency (MHz)", color="#cccccc")
    ax.set_ylabel("RSSI (dBuV)", color="#cccccc")
    ax.tick_params(colors="#cccccc")
    ax.spines[:].set_color("#444444")
    ax.set_xlim(87.5, 108.0)
    ax.set_ylim(0, 120)
    ax.xaxis.set_major_locator(ticker.MultipleLocator(1))
    ax.xaxis.set_minor_locator(ticker.MultipleLocator(0.5))
    ax.yaxis.set_major_locator(ticker.MultipleLocator(20))
    ax.grid(True, which="major", color="#2a2a2a", linewidth=0.8)
    ax.grid(True, which="minor", color="#1a1a1a", linewidth=0.4)
    line_obj, = ax.plot([], [], color="#00cc88", linewidth=1.2)
    title_obj = ax.set_title("Waiting for first scan...", color="#cccccc", fontsize=10)
    plt.tight_layout()
    return fig, ax, line_obj, title_obj

# ── main ──────────────────────────────────────────────────────────────────────

import os, pathlib
pathlib.Path("studio.pid").write_text(str(os.getpid()))

print(f"Opening {PORT} at {BAUD} baud...")
ser = serial.Serial(PORT, BAUD, timeout=15)
print("Handshake...")
handshake(ser)
print("OK — device ready")
setup_scan(ser)

data_queue = queue.Queue()
stop_event  = threading.Event()

worker = threading.Thread(target=serial_worker, args=(ser, data_queue, stop_event), daemon=True)
worker.start()

fig, ax, line_obj, title_obj = build_plot()
fill_holder = [None]   # mutable container so the closure can update it

def animate(frame):
    try:
        data, elapsed_ms, pass_n = data_queue.get_nowait()
    except queue.Empty:
        return

    freqs = sorted(data.keys())
    rssi  = [data[f] for f in freqs]

    line_obj.set_data(freqs, rssi)

    if fill_holder[0] is not None:
        fill_holder[0].remove()
    fill_holder[0] = ax.fill_between(freqs, rssi, alpha=0.25, color="#00cc88")

    n_st   = sum(1 for v in rssi if v >= 20)
    peak_f = freqs[rssi.index(max(rssi))]
    title_obj.set_text(
        f"FM Spectrum  |  pass #{pass_n}  |  {elapsed_ms:.0f} ms  |  "
        f"{len(data)} pts  |  peak: {max(rssi)} dBuV @ {peak_f:.1f} MHz  |  "
        f"stations >=20 dBuV: {n_st}"
    )
    print(f"Pass {pass_n}: {elapsed_ms:.0f} ms  peak={max(rssi)} dBuV @ {peak_f:.1f} MHz")

ani = FuncAnimation(fig, animate, interval=100, cache_frame_data=False)

try:
    plt.show()
except KeyboardInterrupt:
    pass
finally:
    stop_event.set()
    ser.close()
    pathlib.Path("studio.pid").unlink(missing_ok=True)
    print("Done.")
