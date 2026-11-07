"""A dependency-free Tetris game. Run with Python 3 and Tkinter."""
import random
import math
import time
import tkinter as tk

WIDTH, HEIGHT, CELL = 10, 20, 44
SHAPES = {
    'I': ((0, 1), (1, 1), (2, 1), (3, 1)),
    'O': ((1, 0), (2, 0), (1, 1), (2, 1)),
    'T': ((1, 0), (0, 1), (1, 1), (2, 1)),
    'S': ((1, 0), (2, 0), (0, 1), (1, 1)),
    'Z': ((0, 0), (1, 0), (1, 1), (2, 1)),
    'J': ((0, 0), (0, 1), (1, 1), (2, 1)),
    'L': ((2, 0), (0, 1), (1, 1), (2, 1)),
}
COLORS = dict(zip(SHAPES, ('#22d3ee', '#fde047', '#c084fc', '#4ade80', '#fb7185', '#60a5fa', '#fb923c')))


class Game:
    def __init__(self):
        self.reset()

    def reset(self):
        self.board = [[None] * WIDTH for _ in range(HEIGHT)]
        self.bag = []
        self.score = self.lines = 0
        self.over = self.paused = False
        self.last_clear = []
        self.next = self.pick()
        self.spawn()

    @property
    def level(self):
        return self.lines // 10 + 1

    def pick(self):
        if not self.bag:
            self.bag = list(SHAPES)
            random.shuffle(self.bag)
        return self.bag.pop()

    def spawn(self):
        self.kind, self.next = self.next, self.pick()
        self.cells = SHAPES[self.kind]
        self.x, self.y = 3, 0
        self.over = not self.valid(self.cells, self.x, self.y)

    def valid(self, cells, x, y):
        return all(0 <= x + a < WIDTH and 0 <= y + b < HEIGHT
                   and self.board[y + b][x + a] is None for a, b in cells)

    def move(self, dx, dy):
        if self.over or self.paused:
            return False
        if self.valid(self.cells, self.x + dx, self.y + dy):
            self.x += dx
            self.y += dy
            return True
        return False

    def rotate(self):
        if self.over or self.paused or self.kind == 'O':
            return
        pivot = 1.5 if self.kind == 'I' else 1
        rotated = tuple((int(2 * pivot - b), a) for a, b in self.cells)
        for dx, dy in ((0, 0), (-1, 0), (1, 0), (-2, 0), (2, 0), (0, -1), (0, -2)):
            if self.valid(rotated, self.x + dx, self.y + dy):
                self.cells = rotated
                self.x += dx
                self.y += dy
                return

    def lock(self):
        for a, b in self.cells:
            self.board[self.y + b][self.x + a] = self.kind
        self.last_clear = [y for y, row in enumerate(self.board) if all(row)]
        remaining = [row for row in self.board if not all(row)]
        cleared = HEIGHT - len(remaining)
        self.score += (0, 100, 300, 500, 800)[cleared] * self.level
        self.lines += cleared
        self.board = [[None] * WIDTH for _ in range(cleared)] + remaining
        self.spawn()

    def step(self, soft=False):
        if self.over or self.paused:
            return
        if self.move(0, 1):
            self.score += int(soft)
        else:
            self.lock()

    def drop(self):
        if self.over or self.paused:
            return
        while self.move(0, 1):
            self.score += 2
        self.lock()


# Logical coordinates keep the enlarged board proportional on smaller screens.
SCENE_W, SCENE_H = 780, 960
BOARD_X, BOARD_Y = 300, 40


def mix(color, target, amount):
    a = tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))
    b = tuple(int(target[i:i + 2], 16) for i in (1, 3, 5))
    return '#' + ''.join(f'{round(x + (y - x) * amount):02x}' for x, y in zip(a, b))


class App:
    """A resizable, dependency-free cosmic arcade rendered on a Tk canvas."""

    def __init__(self, root):
        self.root, self.game = root, Game()
        self.best = 0
        self.scale = 1.0
        self.particles = []
        self.notice = ''
        self.notice_until = 0
        self.resize_timer = None
        self.closed = False
        self.hover = None
        self.space_time = 0.0
        self.rng = random.Random(7401)
        self.stars = [(self.rng.uniform(0, SCENE_W), self.rng.uniform(0, SCENE_H),
                       self.rng.choice((0.6, 0.7, 1, 1.4, 2)), self.rng.random())
                      for _ in range(260)]
        root.title('PRISM · Cosmic Tetris')
        root.configure(bg='#050817')
        fit = min(1, (root.winfo_screenheight() - 100) / SCENE_H,
                  (root.winfo_screenwidth() - 80) / SCENE_W)
        root.geometry(f'{int(SCENE_W * fit)}x{int(SCENE_H * fit)}')
        root.minsize(468, 576)
        self.canvas = tk.Canvas(root, bg='#050817', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)
        root.bind('<KeyPress>', self.key)
        self.canvas.bind('<Configure>', self.resize)
        self.canvas.bind('<Button-1>', self.click)
        self.canvas.bind('<Motion>', self.motion)
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.timer = root.after(650, self.tick)
        self.animation = root.after(40, self.animate)
        self.last_frame = time.monotonic()

    def resize(self, event):
        if self.resize_timer is not None:
            self.root.after_cancel(self.resize_timer)
        self.resize_timer = self.root.after(120, self.scene)

    def scene(self):
        self.resize_timer = None
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        self.scale = min(w / SCENE_W, h / SCENE_H)
        self.ox = (w - SCENE_W * self.scale) / 2
        self.oy = (h - SCENE_H * self.scale) / 2
        self.canvas.delete('all')
        # A deterministic, low-resolution nebula is generated with the standard
        # library, then enlarged by Tk. No asset downloads or image libraries.
        iw, ih = max(1, math.ceil(w / 2)), max(1, math.ceil(h / 2))
        image = tk.PhotoImage(width=iw, height=ih)
        rows = []
        for py in range(ih):
            y = (py * 2 - self.oy) / self.scale
            row = []
            for px in range(iw):
                x = (px * 2 - self.ox) / self.scale
                wave = x - (435 + 95 * math.sin(y / 125) + 40 * math.sin(y / 49))
                cloud = math.exp(-(wave / 110) ** 2)
                texture = (math.sin(x / 23 + math.sin(y / 31)) *
                           math.sin(y / 37 + x / 58) + 1) / 2
                violet = cloud * (0.3 + 0.7 * texture)
                blue = math.exp(-((x - 620) / 180) ** 2 - ((y - 270) / 210) ** 2)
                # Keep the playfield readable while retaining a visible galaxy.
                inside = BOARD_X <= x <= BOARD_X + WIDTH * CELL and BOARD_Y <= y <= BOARD_Y + HEIGHT * CELL
                shade = 0.75 if inside else 1
                r = int(5 + 55 * violet * shade)
                g = int(8 + 16 * violet * shade + 14 * blue)
                b = int(20 + 95 * violet * shade + 38 * blue)
                row.append(f'#{r:02x}{g:02x}{b:02x}')
            rows.append('{' + ' '.join(row) + '}')
        image.put(' '.join(rows))
        self.background = image.zoom(2)
        c = self.canvas
        c.create_image(0, 0, image=self.background, anchor='nw', tags='background')
        for x, y, radius, brightness in self.stars:
            color = mix('#3d487d', '#d9eaff', brightness)
            c.create_oval(x-radius, y-radius, x+radius, y+radius,
                          fill=color, outline='', tags='scene')
            if radius == 2:
                c.create_line(x-5, y, x+5, y, fill='#7289b2', tags='scene')
                c.create_line(x, y-5, x, y+5, fill='#7289b2', tags='scene')
        # A crescent planet and an orbit live INSIDE the playable area.
        c.create_oval(598, 163, 670, 235, fill='#654eac', outline='#a28bdd', tags='scene')
        c.create_oval(606, 160, 674, 228, fill='#10152f', outline='', tags='scene')
        c.create_arc(335, 140, 900, 500, start=90, extent=105,
                     style='arc', outline='#3c3c76', tags='scene')
        x, y, bw, bh = BOARD_X, BOARD_Y, WIDTH * CELL, HEIGHT * CELL
        for inset, color in ((-10, '#111b35'), (-7, '#2e4665'), (-4, '#0b2038'), (-2, '#54dcf5')):
            c.create_rectangle(x+inset, y+inset, x+bw-inset, y+bh-inset,
                               outline=color, width=2, tags='scene')
        for col in range(WIDTH + 1):
            c.create_line(x+col*CELL, y, x+col*CELL, y+bh, fill='#23314b', tags='scene')
        for row in range(HEIGHT + 1):
            c.create_line(x, y+row*CELL, x+bw, y+row*CELL, fill='#23314b', tags='scene')
        c.scale('scene', 0, 0, self.scale, self.scale)
        c.move('scene', self.ox, self.oy)
        self.draw()

    def rect(self, x, y, w, h, fill, outline='', width=1):
        return self.canvas.create_rectangle(x, y, x+w, y+h, fill=fill,
                                            outline=outline, width=width, tags='dynamic')

    def text(self, x, y, text, size=12, color='#e8f3ff', bold=False, anchor='nw'):
        return self.canvas.create_text(x, y, text=text, fill=color, anchor=anchor,
            font=('Helvetica', max(7, round(size * self.scale)), 'bold' if bold else 'normal'),
            tags='dynamic')

    def panel(self, x, y, w, h):
        self.rect(x+3, y+5, w, h, '#030613')
        self.rect(x, y, w, h, '#0a1328', '#304e70')
        self.rect(x+1, y+1, w-2, 2, '#52658b')

    def block(self, x, y, color):
        c, n = self.canvas, CELL
        x, y, n = x+2, y+2, n-4
        bevel = 5
        self.rect(x+2, y+3, n, n, '#030713')
        self.rect(x, y, n, n, color)
        c.create_polygon(x,y, x+n,y, x+n-bevel,y+bevel, x+bevel,y+bevel,
                         fill=mix(color, '#ffffff', .55), outline='', tags='dynamic')
        c.create_polygon(x,y, x+bevel,y+bevel, x+bevel,y+n-bevel, x,y+n,
                         fill=mix(color, '#ffffff', .23), outline='', tags='dynamic')
        c.create_polygon(x+n,y, x+n,y+n, x+n-bevel,y+n-bevel, x+n-bevel,y+bevel,
                         fill=mix(color, '#05091b', .42), outline='', tags='dynamic')
        c.create_polygon(x,y+n, x+bevel,y+n-bevel, x+n-bevel,y+n-bevel, x+n,y+n,
                         fill=mix(color, '#05091b', .6), outline='', tags='dynamic')
        self.rect(x+bevel, y+bevel, n-2*bevel, n-2*bevel, '', mix(color, '#ffffff', .12))

    def draw(self):
        if not hasattr(self, 'background') or self.closed:
            return
        c, g = self.canvas, self.game
        c.delete('dynamic')
        self.draw_space()
        self.text(28, 49, 'P R I S M', 28, '#eafaff', True)
        self.text(30, 94, 'C O S M I C   T E T R I S', 9, '#83cbdf')
        c.create_line(30, 122, 253, 122, fill='#3b7394', tags='dynamic')
        self.panel(28, 156, 230, 128)
        self.text(45, 173, 'C U R R E N T   R U N', 9, '#90a7c5')
        self.text(43, 200, f'{g.score:06d}', 31, '#cefbff', True)
        self.text(46, 252, 'P O I N T S', 9, '#46dfed')
        for x, label, value in ((28, 'LEVEL', f'{g.level:02d}'), (151, 'LINES', f'{g.lines:03d}')):
            self.panel(x, 305, 107, 110)
            self.text(x+16, 322, label, 10, '#90a7c5')
            self.text(x+15, 350, value, 27, '#e0faff', True)
        self.panel(28, 437, 230, 104)
        self.text(45, 454, 'NEXT LEVEL', 10, '#90a7c5')
        self.rect(45, 484, 195, 10, '#192540')
        if g.lines % 10:
            self.rect(45, 484, 195*(g.lines % 10)/10, 10, '#35d4e9')
        self.text(45, 507, f'{10-g.lines % 10} lines to level {g.level+1}', 10, '#7089ab')
        self.panel(28, 563, 230, 105)
        self.text(45, 581, 'SESSION BEST', 10, '#90a7c5')
        self.text(43, 609, f'{self.best:06d}', 24, '#d8d3ff', True)
        for name, y, caption in (('pause', 723, 'RESUME' if g.paused else 'PAUSE'),
                                  ('restart', 787, 'RESTART')):
            self.rect(28, y, 230, 47, '#142d46' if self.hover == name else '#0b1a30',
                      '#6ceaf1' if self.hover == name else '#3d7594')
            self.text(143, y+23, caption, 12, '#d4f7ff', True, 'center')
        self.text(30, 883, 'F I N D   Y O U R   O R B I T .', 9, '#9ca9ce')
        self.text(30, 907, 'PYTHON / TKINTER', 8, '#536684')
        for row, cells in enumerate(g.board):
            for col, kind in enumerate(cells):
                if kind:
                    self.block(BOARD_X+col*CELL, BOARD_Y+row*CELL, COLORS[kind])
        if not g.over:
            for a,b in g.cells:
                self.block(BOARD_X+(g.x+a)*CELL, BOARD_Y+(g.y+b)*CELL, COLORS[g.kind])
        now = time.monotonic()
        for x,y,vx,vy,life,color in self.particles:
            if BOARD_X+3 < x < BOARD_X+WIDTH*CELL-3 and BOARD_Y+3 < y < BOARD_Y+HEIGHT*CELL-3:
                radius = max(1, life*3)
                self.rect(x-radius, y-radius, radius*2, radius*2, mix('#0b1228', color, min(1, life)))
        if now < self.notice_until:
            self.rect(BOARD_X+65, 405, WIDTH*CELL-130, 54, '#0b1730', '#5c88ae')
            self.text(BOARD_X+WIDTH*CELL/2, 432, self.notice, 18, '#c5faff', True, 'center')
        if g.over or g.paused:
            self.rect(BOARD_X+28, 365, WIDTH*CELL-56, 180, '#081226', '#67d5eb', 2)
            self.text(BOARD_X+WIDTH*CELL/2, 407, 'GAME OVER' if g.over else 'PAUSED',
                      25, '#e3faff', True, 'center')
            self.text(BOARD_X+WIDTH*CELL/2, 454, f'Score  {g.score:,}' if g.over else 'A moment between stars.',
                      12, '#99adcc', anchor='center')
            self.text(BOARD_X+WIDTH*CELL/2, 501, 'Press R to try again' if g.over else 'Press P to resume',
                      11, '#4cd9e7', anchor='center')
        c.scale('dynamic', 0, 0, self.scale, self.scale)
        c.move('dynamic', self.ox, self.oy)

    def draw_space(self):
        """Decorative objects stay behind blocks and never touch game state."""
        c, t = self.canvas, self.space_time
        # Two short meteor passes, staggered to avoid a busy playfield.
        for offset, y0 in ((0, 130), (3.7, 450)):
            phase = (t+offset) % 7
            if phase < 1.6:
                q = phase/1.6
                x = BOARD_X+60+q*300
                y = BOARD_Y+y0+q*130
                c.create_line(x-42, y-18, x, y, fill='#31486a', width=2, tags='dynamic')
                c.create_line(x-18, y-8, x, y, fill='#7ba8bd', tags='dynamic')
                self.rect(x-1, y-1, 3, 3, '#b6d7e1')
        # A distant saucer travels slowly across the upper half of the board.
        x = BOARD_X+35+(t*13) % (WIDTH*CELL-70)
        y = BOARD_Y+290+24*math.sin(t*.45)
        c.create_oval(x-5, y-7, x+5, y+3, fill='#334064', outline='#53668b', tags='dynamic')
        c.create_oval(x-15, y-1, x+15, y+6, fill='#263b5b', outline='#547a94', tags='dynamic')
        for dx in (-8, 0, 8):
            self.rect(x+dx-1, y+3, 2, 1, '#88a7bb')
        # A tiny rocket ascends well inside the right edge, behind the pieces.
        x = BOARD_X+WIDTH*CELL-55+8*math.sin(t*.4)
        y = BOARD_Y+HEIGHT*CELL-45-(t*23) % (HEIGHT*CELL-100)
        c.create_polygon(x,y-12, x-5,y-3, x-5,y+9, x+5,y+9, x+5,y-3,
                         fill='#465675', outline='#7382a0', tags='dynamic')
        c.create_polygon(x-5,y+3, x-10,y+12, x-4,y+9,
                         fill='#536383', outline='', tags='dynamic')
        c.create_polygon(x+5,y+3, x+10,y+12, x+4,y+9,
                         fill='#536383', outline='', tags='dynamic')
        c.create_oval(x-2,y-2,x+2,y+2, fill='#89bac7', outline='', tags='dynamic')
        c.create_polygon(x-3,y+10, x,y+19+3*math.sin(t*16), x+3,y+10,
                         fill='#ba8376', outline='', tags='dynamic')

    def effects(self, old_board, old_lines):
        g = self.game
        self.best = max(self.best, g.score)
        if old_board is g.board:
            return
        if g.lines > old_lines:
            self.notice = ('SINGLE', 'DOUBLE', 'TRIPLE', 'TETRIS!')[g.lines-old_lines-1]
            self.notice_until = time.monotonic()+.8
            for row in g.last_clear:
                for _ in range(30):
                    self.particles.append([BOARD_X+self.rng.uniform(4, WIDTH*CELL-4),
                        BOARD_Y+(row+.5)*CELL, self.rng.uniform(-100,100),
                        self.rng.uniform(-180,30), self.rng.uniform(.4,1), '#a5ebff'])
        else:
            for _ in range(14):
                self.particles.append([BOARD_X+(g.x+1.5)*CELL,
                    BOARD_Y+HEIGHT*CELL-8, self.rng.uniform(-100,100),
                    self.rng.uniform(-110,-20), .45, COLORS[g.kind]])

    def key(self, event):
        g, key = self.game, event.keysym.lower()
        board, lines = g.board, g.lines
        if key == 'escape':
            self.close()
            return
        if key == 'r':
            self.root.after_cancel(self.timer)
            g.reset()
            self.particles.clear()
            self.notice_until = 0
            self.timer = self.root.after(650, self.tick)
        elif key == 'p' and not g.over:
            g.paused = not g.paused
        elif key in ('left', 'a'):
            g.move(-1, 0)
        elif key in ('right', 'd'):
            g.move(1, 0)
        elif key in ('up', 'w'):
            g.rotate()
        elif key in ('down', 's'):
            g.step(soft=True)
        elif key == 'space':
            g.drop()
        if key != 'r':
            self.effects(board, lines)
        self.draw()

    def button_at(self, event):
        if not hasattr(self, 'ox'):
            return None
        x, y = (event.x-self.ox)/self.scale, (event.y-self.oy)/self.scale
        if 28 <= x <= 258:
            if 723 <= y <= 770:
                return 'pause'
            if 787 <= y <= 834:
                return 'restart'
        return None

    def click(self, event):
        from types import SimpleNamespace
        button = self.button_at(event)
        if button:
            self.key(SimpleNamespace(keysym='p' if button == 'pause' else 'r'))
        self.canvas.focus_set()

    def motion(self, event):
        button = self.button_at(event)
        if button != self.hover:
            self.hover = button
            self.canvas.configure(cursor='hand2' if button else '')
            self.draw()

    def tick(self):
        board, lines = self.game.board, self.game.lines
        self.game.step()
        self.effects(board, lines)
        self.draw()
        self.timer = self.root.after(max(80, 650-(self.game.level-1)*50), self.tick)

    def animate(self):
        now = time.monotonic()
        dt = min(.08, now-self.last_frame)
        self.last_frame = now
        dirty = bool(self.particles) or bool(self.notice_until) or not self.game.paused and not self.game.over
        if not self.game.paused and not self.game.over:
            self.space_time += dt
            for p in self.particles:
                p[0] += p[2]*dt
                p[1] += p[3]*dt
                p[3] += 140*dt
                p[4] -= dt
            self.particles = [p for p in self.particles if p[4] > 0]
        if self.notice_until and now >= self.notice_until:
            self.notice_until = 0
        if dirty:
            self.draw()
        self.animation = self.root.after(40, self.animate)

    def close(self):
        self.closed = True
        for timer in (self.timer, self.animation, self.resize_timer):
            if timer is not None:
                self.root.after_cancel(timer)
        self.root.destroy()


if __name__ == '__main__':
    window = tk.Tk()
    App(window)
    window.mainloop()
