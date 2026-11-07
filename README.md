# PRISM · Cosmic Tetris

A dependency-free Python/Tkinter arcade game with a cosmic playfield, nebula clouds, stars, a crescent planet, and colorful beveled 2.5D blocks. The enlarged 10×20 board has over twice the area of the original at its native design size; the window scales to fit your screen and can be resized.

Shooting stars, a small rocket, and a distant spacecraft move behind the falling pieces. They are decoration only and freeze when you pause or the game ends. There is no landing outline, next-piece panel, or right-side instruction panel. Compact score, level, progress, session-best, and clickable pause/restart controls sit on the left.

Gameplay includes all seven tetrominoes, randomized seven-piece bags, rotation with wall kicks, line-clear particles, scoring, increasing speed, pause, and restart. Session best lasts until you close the app. Artwork is generated locally: no downloads or extra packages.

## Run

Install Python 3.10 or later, then run:

```sh
python tetris.py
```

On Windows, `py tetris.py` also works. On macOS or Linux, use `python3 tetris.py` if needed.
No pip packages are required. Tkinter and a graphical desktop are required; on Ubuntu/Debian, install Tkinter with `sudo apt install python3-tk` if missing.

## Controls

| Key | Action |
| --- | --- |
| Left / Right or A / D | Move |
| Up or W | Rotate clockwise |
| Down or S | Soft drop |
| Space | Hard drop |
| P | Pause / resume |
| R | Restart |
| Escape | Quit |

Single/double/triple/four-line clears award 100/300/500/800 points multiplied by the current level. Every ten cleared lines increases the level. Soft drop awards one point per cell; hard drop awards two.

## Development checks

Run the gameplay regression suite:

```sh
python3 -m unittest discover -s tests -v
```

On a graphical desktop, launch the game and check movement, rotation, soft/hard drop, pause/resume, restart, window resizing, and the clickable buttons. Decorations should freeze on pause and remain behind pieces. The game uses stylized 2.5D blocks rather than a 3D graphics engine.
