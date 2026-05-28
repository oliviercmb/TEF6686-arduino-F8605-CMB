"""FM spectrum scan display — TEF6686 F8605
Triggers a scan via serial, plots RSSI vs frequency with matplotlib.
Live mode: refreshes on every scan pass.
"""
import serial
import time
import sys
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

PORT  = "COM1"
BAUD  = 115200
LIVE  = True   # False = single scan, True = live refresh loop

SCAN_START = 87500   # 87.5 MHz (internal units: kHz/10 = 100 Hz)
SCAN_END   = 108000  # 108.0 MHz
SCAN_STEP  = 100     # 100 kHz step

# ── serial helpers ────────────────────────────────────────────────────────────

def handshake(ser):
    time.sleep(2.0)           # wait for Arduino reset after DTR assertion
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

def do_scan(ser):
    ser.reset_input_buffer()
    ser.write(b"Ss\n")
    t0 = time.perf_counter()
    line = ser.read_until(b"\n", size=8192)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    return parse_scan(line), elapsed_ms

def parse_scan(line: bytes) -> dict:
    result = {}
    line = line.strip()
    if not line.startswith(b"U"):
        return result
    for entry in line[1:].split(b","):
        try:
            f, r = entry.split(b"=")
            freq_mhz = int(f) / 1e6          # internal units are freq*10 Hz -> MHz
            result[freq_mhz] = int(r)
        except ValueError:
            pass
    return result

# ── plot ──────────────────────────────────────────────────────────────────────

def build_plot():
    fig, ax = plt.subplots(figsize=(14, 5))
    fig.patch.set_facecolor("#0d0d0d")
    ax.set_facecolor("#0d0d0d")
    ax.set_xlabel("Frequency (MHz)", color="#cccccc")
    ax.set_ylabel("RSSI (dBµV)", color="#cccccc")
    ax.tick_params(colors="#cccccc")
    ax.spines[:].set_color("#444444")
    ax.set_xlim(87.5, 108.0)
    ax.set_ylim(0, 120)
    ax.xaxis.set_major_locator(ticker.MultipleLocator(1))
    ax.xaxis.set_minor_locator(ticker.MultipleLocator(0.5))
    ax.yaxis.set_major_locator(ticker.MultipleLocator(20))
    ax.grid(True, which="major", color="#2a2a2a", linewidth=0.8)
    ax.grid(True, which="minor", color="#1a1a1a", linewidth=0.4)
    line, = ax.plot([], [], color="#00cc88", linewidth=1.2)
    fill = ax.fill_between([], [], alpha=0.25, color="#00cc88")
    title = ax.set_title("", color="#cccccc", fontsize=10)
    plt.tight_layout()
    return fig, ax, line, fill, title

def update_plot(ax, line_obj, fill_obj, title_obj, data: dict, elapsed_ms: float, pass_n: int):
    if not data:
        return None, None
    freqs = sorted(data.keys())
    rssi  = [data[f] for f in freqs]

    line_obj.set_data(freqs, rssi)

    # redraw fill_between
    for coll in ax.collections:
        coll.remove()
    fill = ax.fill_between(freqs, rssi, alpha=0.25, color="#00cc88")

    n_stations = sum(1 for v in rssi if v >= 20)
    title_obj.set_text(
        f"FM Spectrum — pass #{pass_n}  |  {elapsed_ms:.0f} ms  |  "
        f"{len(data)} pts  |  stations ≥20 dBµV: {n_stations}"
    )
    return fill

# ── main ──────────────────────────────────────────────────────────────────────

print(f"Opening {PORT} at {BAUD} baud...")
with serial.Serial(PORT, BAUD, timeout=15) as ser:
    print("Handshake...")
    handshake(ser)
    print("OK — device ready")
    setup_scan(ser)

    fig, ax, line_obj, fill_obj, title_obj = build_plot()
    plt.ion()
    plt.show()

    pass_n = 0
    try:
        while True:
            pass_n += 1
            data, elapsed_ms = do_scan(ser)
            if not data:
                print(f"Pass {pass_n}: empty response")
            else:
                fill_obj = update_plot(ax, line_obj, fill_obj, title_obj, data, elapsed_ms, pass_n)
                freqs = sorted(data.keys())
                rssi  = [data[f] for f in freqs]
                peak_f = freqs[rssi.index(max(rssi))]
                print(f"Pass {pass_n}: {elapsed_ms:.0f} ms  "
                      f"pts={len(data)}  peak={max(rssi)} dBµV @ {peak_f:.1f} MHz")
            plt.pause(0.05)
            if not LIVE:
                break
    except KeyboardInterrupt:
        print("\nStopped.")

plt.ioff()
plt.show()
