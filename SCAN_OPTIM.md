# FM Sweep Speed Optimisation — TEF6686

## Problem

File: `TEF6686_arduino_F8605_CMB.ino`, function `scan()` around line 903.

```cpp
Set_Cmd(scan_mode == 0 ? 32 : 33, 1, 2, 1, freq);
delay(10);  // ← culprit, line 928
Get_Cmd(scan_mode == 0 ? 32 : 33, 128, uQuality, 4);
```

Over the European FM band (87.5–108 MHz, 100 kHz step = 206 frequencies):
- 206 × 10 ms = ~2 s in delays alone
- Plus I²C transactions at 100 kHz (Arduino Nano default)

---

## Optimisation levers

### 1. I²C at 400 kHz — mandatory 50 µs guard (V205)

The V205 manual (§5.6) documents a constraint absent from V102:
**50 µs minimum** between the end of a write transaction and the start of a read transaction.

Two options:
- **Option A**: stay at ≤ 184 kHz — setup time satisfied without extra delay
- **Option B**: use 400 kHz + add `delayMicroseconds(27)` between the write stop and read start

```cpp
Wire.setClock(400000);
// between Set_Cmd and Get_Cmd:
delayMicroseconds(27);  // ensures the required 50 µs
```

> Without this guard at 400 kHz, reads may return `0x0000` or `0xFFF8` (bus error).

### 2. Reducing delay(10)

The `delay(10)` is empirical — no minimum value is documented in the V102 manual.

The V205 manual (§4.1.1) provides the following reference values:
- A complete **AF_Update cycle** (mode=3) finishes in **6 ms** including mute/demute
- The internal AF_Update measurement time is **2 ms** (75% settling of the offset detector)
- For Search (mode=2): no specific figure, but the chip stays muted — detectors do not need
  to fully converge for an RSSI-only sweep

For a spectrum sweep (RSSI only), test in steps:
```
10 ms → 7 ms → 5 ms → 3 ms → 2 ms
```
Validate that `uQuality[1]` (RSSI) is stable and consistent at each step.

### 3. Get_Quality_Status vs Get_Quality_Data (V205 only)

V205 defines two distinct commands:
- **cmd 128 `Get_Quality_Status`** — returns status + data, does not flush AF_Update data
- **cmd 129 `Get_Quality_Data`** — returns status + data, flushes after read

For a sweep: use **cmd 128** (already the case in the current code — correct).

### 4. Search mode (mode=2) vs Preset (mode=1)

The original code used mode=1 (Preset) for each step of the sweep. Preset triggers a 10 ms mute
slope and resets the detectors at every frequency — with 206 steps this causes mute/demute churn
and leaves the chip in an unstable state at the end of the scan.

Mode=2 (Search) keeps the chip muted throughout the entire sweep: no slope overhead, instant
retune at each step, and a clean single Preset at the end to restore normal operation.

```cpp
Set_Cmd(32, 1, 2, 2, scan_start);   // Search: mute chip for entire sweep
Set_Cmd(scan_mode == 0 ? 32 : 33, 1, 2, 2, freq);  // instant retune per step
```

---

## Baseline measurement

```cpp
uint32_t t0 = millis();
scan(false);
Serial.println(millis() - t0);
```

---

## Results

| Configuration | Sweep time (87.5–108 MHz) |
|---------------|--------------------------|
| Baseline (mode=1, delay=10ms, I²C 100kHz) | ~2616 ms |
| Optimised (mode=2, delay=5ms, I²C 400kHz) | ~1335 ms |
| **Gain** | **×2.0** |

Validated on hardware (TEF6686 F8605 Lithio HW 2.2 / FW 5.00, Arduino Nano, COM1).
No RSSI artifacts at delay=5ms; deviation < 1 dBµV vs live cmd-129 readings at strong stations.

---

## Documented timings (V205)

| Action | Documented timing |
|--------|------------------|
| Preset mute FM | ~32 ms |
| Preset mute AM | ~60 ms |
| Search/Preset mute slope | 10 ms (if not already muted) / 0 ms (if already muted) |
| AF_Update full cycle | 6 ms |
| AF_Update quality measurement | 2 ms (75% offset detector settling) |
| Jump/Check/AF_Update mute slope | 1 ms |
| Check mute minimum (End) | ~16 ms |
| FM↔AM band change | +15 ms max |
| Read delay after write at 400 kHz | 50 µs min (27 µs added delay sufficient) |

---

## Notes
- User Manual V102: `UserManual_TEF668X_V102.pdf`
- User Manual V205: `UM_Radio_TEF668XA_V205-1.pdf`
- `uQuality[1]` = LEVEL (RSSI ×10, divide by 10 to get dBµV)
- Mode 2 (Search) keeps chip muted — no detector reset between steps
- Timings above are from the V205 manual; V102 does not document these values
