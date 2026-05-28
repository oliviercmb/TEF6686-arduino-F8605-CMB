# TEF6686 Arduino F8605 — CMB fork

Arduino firmware for the NXP TEF6686 (F8605) FM/AM receiver chip, compatible with XDR-GTK / TEF-GTK v1.1.2.

## Credits

This firmware is a fork of the work by:

- **Eustake (marsel90)** — original sketch, F8602/F8605 compatibility, MPX output, iMS/EQ support
- **VoXiTPro** — filter switching, stereo control, AGC improvements, signal measurement
- FMDXklaas, ODJeetje and others for testing and improvements

## Changes in this fork (oliviercmb / F8605-CMB)

### XDR-GTK protocol fixes
- `W` command remapped to IF bandwidth (XDR protocol)
- `G` command handles EQ+iMS per XDR protocol
- Trailing comma removed from scan `U` output
- `Serial.println` replaced with `print+LF` to avoid CRLF in protocol responses
- `FMFilterMap[-1]` out-of-bounds access prevented in M and T handlers

### FM sweep optimisation
- **Search mode (mode=2)** for scan: chip stays muted throughout the sweep, no mute/demute churn at each step — instant retune after first step
- **I²C at 400 kHz** with 50 µs stop-to-start guard (per NXP V205 spec)
- **5 ms per-frequency delay**: validated against live RSSI on strongest stations, no -30 dBuV artifacts
- 30 ms initial settle before first read
- **Result: FM sweep 87.5–108 MHz in ~1335 ms vs ~2616 ms baseline (×2.0)**

## Hardware

- Arduino Nano V3.0 (ATmega328P, 5V)
- NXP TEF6686 F8605 (Lithio, HW rev 2.2, FW V5.00)
- I²C at 400 kHz

## Usage

Open with Arduino IDE, select **Arduino Nano (ATmega328P)**, upload to COM port.  
Use with [XDR-GTK](https://github.com/kkonradpl/xdr-gtk) or TEF-GTK v1.1.2.
