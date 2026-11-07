# Codex Tetris — 11.07.26

A desktop Tetris game written in Python with Tkinter. Includes all seven tetrominoes, randomized seven-piece bags, rotation with wall kicks, next-piece preview, ghost piece, line clearing, scores, increasing speed, pause and restart.

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
