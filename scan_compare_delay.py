"""Compare FM scan at delay=3ms vs delay=5ms — does settling time affect apparent filter width?"""
import serial, time, sys, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

PORT  = "COM1"
BAUD  = 115200
SCAN_START = 87500
SCAN_END   = 108000
SCAN_STEP  = 100

# Patch delay value in firmware via scan_step trick is not possible —
# instead we measure two consecutive scans with the SAME firmware
# and overlay them to check stability. To compare delays, flash manually.
# This script just does N scans and overlays them to check consistency.

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

SCANS = 3

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

    results = []
    for i in range(SCANS):
        data, elapsed = do_scan(ser)
        results.append((data, elapsed))
        print(f"Scan {i+1}: {elapsed:.0f} ms, {len(data)} pts")
        time.sleep(0.1)

freqs = sorted(results[0][0].keys())

fig, ax = plt.subplots(figsize=(14, 5))
fig.patch.set_facecolor("#0d0d0d")
ax.set_facecolor("#0d0d0d")
ax.set_xlabel("Frequency (MHz)", color="#cccccc")
ax.set_ylabel("RSSI (dBuV)", color="#cccccc")
ax.tick_params(colors="#cccccc")
for s in ax.spines.values(): s.set_color("#444444")
ax.set_xlim(87.5, 108.0); ax.set_ylim(0, 120)
ax.xaxis.set_major_locator(ticker.MultipleLocator(1))
ax.xaxis.set_minor_locator(ticker.MultipleLocator(0.5))
ax.grid(True, which="major", color="#2a2a2a", linewidth=0.8)
ax.grid(True, which="minor", color="#1a1a1a", linewidth=0.4)

colors = ["#00cc88", "#cc8800", "#0088cc"]
for i, (data, elapsed) in enumerate(results):
    rssi = [data.get(f, 0) for f in freqs]
    ax.plot(freqs, rssi, color=colors[i], linewidth=1.0, alpha=0.8, label=f"Pass {i+1} — {elapsed:.0f} ms")

avg_ms = sum(r[1] for r in results) / len(results)
ax.legend(facecolor="#1a1a1a", labelcolor="#cccccc", fontsize=9)
ax.set_title(f"FM Scan stability — {SCANS} passes — avg {avg_ms:.0f} ms/sweep", color="#cccccc", fontsize=10)
plt.tight_layout()
plt.savefig("spectrum_stability.png", dpi=150, facecolor="#0d0d0d")
print(f"Saved: spectrum_stability.png  (avg {avg_ms:.0f} ms)")
