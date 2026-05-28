# TEF6686 Arduino F8605 — CMB fork

Arduino firmware for the NXP TEF6686 (F8605) FM/AM receiver chip, compatible with XDR-GTK.

## Credits

This firmware is a fork of the work by:

- **Eustake (marsel90)** — original sketch, F8602/F8605 compatibility, MPX output, iMS/EQ support
- **VoXiTPro** — filter switching, stereo control, AGC improvements, signal measurement
- FMDXklaas, ODJeetje and others for testing and improvements

## Changes in this fork (oliviercmb / F8605-CMB)

### Protocol — XDR-GTK compatibility
- `W` command remapped to IF bandwidth control (Hz), 0 = auto
- `G` command remapped to EQ + iMS (per XDR-GTK protocol)
- `C` command remapped to RF+IF gain (legacy)
- `F` command: distinguishes poll (no argument) vs set
- `I` command added: reads chip identification (type, HW rev, FW version)
- `T` command: OOB access on `FMFilterMap[-1]` fixed
- `M` command: OOB access on `FMFilterMap[-1]` fixed
- Serial protocol: `Serial.println` replaced with `print+LF` — avoids CRLF breaking XDR-GTK parsing
- Scan `U` output: trailing comma removed

### Code structure
- `SERIAL_BUFFER_SIZE` increased 16 → 20 (handles longer commands)
- `radio_mode` initialized to -1 (avoids undefined state before first tune)
- Added `MODE_FM` / `MODE_AM` defines
- Added `QUAL_*` defines for all quality fields (STAT, LEVL, USN, WAM, OFST, BWTH, MODU, SNR, NOIS, COCH)
- Added `watch_freq` variable
- Updated DSP initialization data

### FM sweep optimisation
- **Search mode (mode=2)**: chip stays muted throughout the sweep — no mute/demute churn at each step, instant retune after first step
- **I²C at 400 kHz** with 50 µs stop-to-start guard (per NXP TEF668X V205 spec)
- **5 ms per-frequency settling delay** — eliminates -30 dBuV artifacts on weak/empty channels
- 30 ms initial settle before first read
- **Result: FM sweep 87.5–108 MHz in ~1335 ms vs ~2616 ms baseline (×2.0), validated in XDR-GTK**

## Hardware

- Arduino Nano V3.0 (ATmega328P, 5V)
- NXP TEF6686 F8605 Lithio (HW rev 2.2, FW V5.00)
- I²C at 400 kHz

## Usage

Open with Arduino IDE, select **Arduino Nano (ATmega328P)**, upload to your COM port.  
Use with [XDR-GTK](https://github.com/kkonradpl/xdr-gtk).
