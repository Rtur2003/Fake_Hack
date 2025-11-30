# System Hack Simulator

Visual hacking simulator with real system stats, cinematic terminal logs, and a pixel-war finale. **No real hacking is performed.**

---

## Features
- Phase-driven script: Recon -> Breach -> Pivot -> Exfil -> Cleanup with live system fingerprinting and OP code
- Real telemetry: CPU/RAM/disk, OS/user/host info, top processes, live connections, data siphon meter
- Immersive terminal: timestamped logs, phase badge, threat indicator, progress bar
- Pixel war and glitch-to-overlay finale: full-screen battle plus typewritten watcher messages that break the 4th wall
- Safety controls: ESC or on-screen EXIT button; optional input block

---

## Installation
1) Python 3.8+  
2) Install dependencies:
```bash
pip install -r requirements.txt
```

---

## Usage
```bash
python hacked.py [options]
```

Key options:
- `--duration SECONDS`     main simulation length (default 90s)
- `--auto-close SECONDS`   extra wait after pixel war (default 35s)
- `--no-fullscreen`        windowed mode
- `--no-pixel-war`         skip the pixel battle
- `--block-input`          block keyboard/mouse except ESC
- `--pixel-size N`         pixel size for the war (default 5)
- `--war-tick MS`          tick interval for war updates (default 45ms)
- `--glitch-mode/--no-glitch` enable or disable static-like glitch effect (default on)

Controls:
- `ESC` / `Ctrl+Q` / EXIT button: close immediately
- `F11`: toggle fullscreen
- Static/glitch finale is on by default for a broken-screen vibe; disable with `--no-glitch`.

---

## Notes
- Collects and displays local machine statistics only.
- Uses: `tkinter` (UI), `psutil` (metrics), `pygame` (sound, optional), `Pillow` (image helpers).
- Designed for demos and fun visual effect; keep it ethical.

---

## License
MIT License. Use responsibly.  
Original idea by [@Rtur2003](https://github.com/Rtur2003).
