"""Compare FM scan with narrowest vs widest IF filter to verify filter effect."""
import serial, time, sys, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

PORT  = "COM1"
BAUD  = 115200
SCAN_START = 87500
SCAN_END   = 108000
SCAN_STEP  = 100

def do_scan(ser):
    ser.reset_input_buffer()
    ser.write(b"Ss\n")
    t0 = time.perf_counter()
    line = ser.read_until(b"\n", size=8192)
    elapsed = (time.perf_counter() - t0) * 1000
    data = {}
    for entry in line.strip()[1:].split(b","):
        try:
            f, r = entry.split(b"=")
            data[int(f) / 1000] = int(r)
        except ValueError:
            pass
    return data, elapsed

with serial.Serial(PORT, BAUD, timeout=15) as ser:
    time.sleep(2.0)
    ser.reset_input_buffer()
    ser.write(b"x\n")
    if b"OK" not in ser.read_until(b"OK\n", size=64):
        sys.exit("No OK")
    time.sleep(0.1)

    for cmd in [f"Sa{SCAN_START}\n".encode(), f"Sb{SCAN_END}\n".encode(),
                f"Sc{SCAN_STEP}\n".encode(), b"Sf0\n"]:
        ser.write(cmd); time.sleep(0.05)

    # Scan 1: narrowest filter 56 kHz
    ser.write(b"W5600\n"); time.sleep(0.1)
    data1, t1 = do_scan(ser)
    print(f"56 kHz filter: {t1:.0f} ms, {len(data1)} pts")

    time.sleep(0.3)

    # Scan 2: widest filter 311 kHz
    ser.write(b"W31100\n"); time.sleep(0.1)
    data2, t2 = do_scan(ser)
    print(f"311 kHz filter: {t2:.0f} ms, {len(data2)} pts")

    # Restore auto filter
    ser.write(b"W0\n")

freqs = sorted(data1.keys())
r1 = [data1.get(f, 0) for f in freqs]
r2 = [data2.get(f, 0) for f in freqs]

fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
fig.patch.set_facecolor("#0d0d0d")
for ax, rssi, label, ms, color in [
    (axes[0], r1, "56 kHz  (narrowest)", t1, "#00cc88"),
    (axes[1], r2, "311 kHz (widest)",    t2, "#cc6600"),
]:
    ax.set_facecolor("#0d0d0d")
    ax.tick_params(colors="#cccccc")
    for s in ax.spines.values(): s.set_color("#444444")
    ax.set_ylim(0, 120)
    ax.set_ylabel("RSSI (dBuV)", color="#cccccc")
    ax.xaxis.set_major_locator(ticker.MultipleLocator(1))
    ax.xaxis.set_minor_locator(ticker.MultipleLocator(0.5))
    ax.grid(True, which="major", color="#2a2a2a", linewidth=0.8)
    ax.grid(True, which="minor", color="#1a1a1a", linewidth=0.4)
    ax.plot(freqs, rssi, color=color, linewidth=1.2)
    ax.fill_between(freqs, rssi, alpha=0.2, color=color)
    ax.set_title(f"{label}  |  {ms:.0f} ms", color="#cccccc", fontsize=10)

axes[1].set_xlabel("Frequency (MHz)", color="#cccccc")
fig.suptitle("Filter comparison — if peaks look the same, filter has no effect on scan",
             color="#888888", fontsize=9)
plt.tight_layout()
plt.savefig("spectrum_compare.png", dpi=150, facecolor="#0d0d0d")
print("Saved: spectrum_compare.png")
