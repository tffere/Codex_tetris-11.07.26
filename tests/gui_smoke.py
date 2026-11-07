"""Run explicitly on a desktop: python3 tests/gui_smoke.py."""
import sys
import time
import tkinter as tk
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tetris import App, SHAPES

root = tk.Tk()
errors = []
root.report_callback_exception = lambda *args: errors.append(args)
app = App(root)
try:
    root.update()
    app.scene()
    assert root.title() == 'Tffere Cosmic Tetris'
    assert len(app.canvas.find_withtag('block')) == 4, 'Unexpected landing preview'
    labels = [app.canvas.itemcget(i, 'text') for i in app.canvas.find_all()
              if app.canvas.type(i) == 'text']
    assert 'TFFERE' in labels and not any('UP NEXT' in t or 'PRISM' in t for t in labels)
    x = app.game.x
    app.key(SimpleNamespace(keysym='Left'))
    assert app.game.x == x-1
    app.key(SimpleNamespace(keysym='Up'))
    assert app.game.valid(app.game.cells, app.game.x, app.game.y)
    app.key(SimpleNamespace(keysym='space'))
    assert app.game.score > 0 and any(any(row) for row in app.game.board)
    app.key(SimpleNamespace(keysym='p'))
    frozen, y = app.space_time, app.game.y
    root.after(180, root.quit)
    root.mainloop()
    assert app.space_time == frozen and app.game.y == y
    app.click(SimpleNamespace(x=143*app.scale+app.ox, y=746*app.scale+app.oy))
    assert not app.game.paused
    root.after(180, root.quit)
    root.mainloop()
    assert app.space_time > frozen
    app.key(SimpleNamespace(keysym='r'))
    assert app.game.score == 0 and not any(any(row) for row in app.game.board)
    for geometry in ('468x576', '1000x700', '780x960'):
        root.geometry(geometry)
        root.update()
        root.after(220, root.quit)
        root.mainloop()
        assert app.background.width() > 0
        assert len(app.canvas.find_withtag('block')) == 4
    # Benchmark a dense board to catch expensive per-frame sprite rendering.
    for y in range(10, 20):
        app.game.board[y] = [list(SHAPES)[(x+y)%7] for x in range(10)]
    begin = time.perf_counter()
    for _ in range(20):
        app.draw()
        root.update_idletasks()
    frame_ms = (time.perf_counter()-begin)*1000/20
    assert not errors, errors
    print(f'PASS: assets, branding, no ghost/right panel, controls, decoration pause, restart, resizing; dense-board rendering {frame_ms:.1f} ms/frame')
finally:
    app.close()
