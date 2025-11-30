# System Hack Simulator

Visual hacking simulator with real system stats, cinematic terminal logs, and a pixel-war finale. **No real hacking is performed.**

---

## Features
- Real system data: CPU/RAM/disk, OS/user/host info, top processes, live connections
- Immersive terminal: timestamped logs, status chips, progress bar
- Pixel war finale: full-screen animated color battle (optional)
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
- `--duration SECONDS`     main simulation length (default 35s)
- `--auto-close SECONDS`   extra wait after pixel war (default 15s)
- `--no-fullscreen`        windowed mode
- `--no-pixel-war`         skip the pixel battle
- `--block-input`          block keyboard/mouse except ESC
- `--pixel-size N`         pixel size for the war (default 5)
- `--war-tick MS`          tick interval for war updates (default 60ms)

Controls:
- `ESC` / `Ctrl+Q` / EXIT button: close immediately
- `F11`: toggle fullscreen

---

## Notes
- Collects and displays local machine statistics only.
- Uses: `tkinter` (UI), `psutil` (metrics), `pygame` (sound, optional), `Pillow` (image helpers).
- Designed for demos and fun visual effect; keep it ethical.

---

## License
MIT License. Use responsibly.  
Original idea by [@Rtur2003](https://github.com/Rtur2003).
