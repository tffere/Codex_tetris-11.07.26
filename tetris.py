"""A dependency-free Tetris game. Run with Python 3 and Tkinter."""
import random
import math
import time
import tkinter as tk
from tkinter import font as tkfont
from pathlib import Path

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


def resize_rgb(data, source_width, source_height, width, height):
    """Scale a cached RGB raster without adding a third-party dependency."""
    stride = source_width * 3
    columns = [min(source_width-1, x*source_width//width)*3 for x in range(width)]
    rows = []
    cached_y, cached_row = -1, b''
    for y in range(height):
        sy = min(source_height-1, y*source_height//height)
        if sy != cached_y:
            row = data[sy*stride:(sy+1)*stride]
            cached_row = b''.join(row[x:x+3] for x in columns)
            cached_y = sy
        rows.append(cached_row)
    return b''.join(rows)


class App:
    """A resizable, dependency-free cosmic arcade rendered on a Tk canvas."""

    def __init__(self, root):
        self.root, self.game = root, Game()
        self.best = 0
        families = {f.casefold(): f for f in tkfont.families(root)}
        self.font = next((families[f.casefold()] for f in ('Segoe UI', 'DejaVu Sans', 'Arial', 'Helvetica') if f.casefold() in families), 'Helvetica')
        # Load the bundled artwork once. An explicit format also works on Tk 9.
        source = tk.PhotoImage(master=root, file=str(Path(__file__).resolve().parent / 'assets' / 'nebula.png'), format='png')
        self.texture_width, self.texture_height = source.width(), source.height()
        ppm = source.tk.call(str(source), 'data', '-format', 'ppm')
        self.texture = ppm.split(b'\n', 3)[3]
        self.block_images = {}
        self.scale = 1.0
        self.particles = []
        self.notice = ''
        self.notice_until = 0
        self.resize_timer = None
        self.closed = False
        self.hover = None
        self.space_time = 0.0
        self.rng = random.Random(7401)
        root.title('Tffere Cosmic Tetris')
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
        # Resize only on window changes; animation reuses the same image.
        sw, sh = max(1, round(SCENE_W*self.scale)), max(1, round(SCENE_H*self.scale))
        raster = resize_rgb(self.texture, self.texture_width, self.texture_height, sw, sh)
        self.background = tk.PhotoImage(master=self.root,
            data=f'P6\n{sw} {sh}\n255\n'.encode()+raster, format='ppm')
        self.make_blocks()
        c = self.canvas
        c.create_image(self.ox, self.oy, image=self.background, anchor='nw', tags='background')
        # The asset already contains fine stars, a nebula and a crescent moon.
        # A restrained orbital path remains visible behind the grid.
        c.create_arc(335, 140, 900, 500, start=90, extent=105,
                     style='arc', outline='#514b8a', tags='scene')
        x, y, bw, bh = BOARD_X, BOARD_Y, WIDTH * CELL, HEIGHT * CELL
        for inset, color in ((-8, '#121934'), (-6, '#193759'), (-4, '#3377a4'), (-2, '#5eefff'), (-1, '#c4fcff')):
            c.create_rectangle(x+inset, y+inset, x+bw-inset, y+bh-inset,
                               outline=color, width=2, tags='scene')
        for col in range(WIDTH + 1):
            c.create_line(x+col*CELL, y, x+col*CELL, y+bh, fill='#30365b', tags='scene')
        for row in range(HEIGHT + 1):
            c.create_line(x, y+row*CELL, x+bw, y+row*CELL, fill='#30365b', tags='scene')
        c.scale('scene', 0, 0, self.scale, self.scale)
        c.move('scene', self.ox, self.oy)
        self.draw()

    def rect(self, x, y, w, h, fill, outline='', width=1):
        return self.canvas.create_rectangle(x, y, x+w, y+h, fill=fill,
                                            outline=outline, width=width, tags='dynamic')

    def text(self, x, y, text, size=12, color='#e8f3ff', bold=False, anchor='nw', italic=False, glow=False):
        options = dict(anchor=anchor,
            font=(self.font, max(7, round(size*self.scale)),
                  ('bold' if bold else 'normal')+(' italic' if italic else '')),
            tags='dynamic')
        if glow:
            for dx, dy in ((-1,0),(1,0),(0,-1),(0,1)):
                self.canvas.create_text(x+dx,y+dy,text=text,fill='#234d69',**options)
        return self.canvas.create_text(x,y,text=text,fill=color,**options)

    def rounded(self, x, y, w, h, radius, fill, outline='', width=1):
        r = min(radius, w/2, h/2)
        points = (x+r,y, x+w-r,y, x+w,y, x+w,y+r,
                  x+w,y+h-r, x+w,y+h, x+w-r,y+h,
                  x+r,y+h, x,y+h, x,y+h-r, x,y+r, x,y)
        return self.canvas.create_polygon(points, smooth=True, splinesteps=16,
            fill=fill, outline=outline, width=width, tags='dynamic')

    def panel(self, x, y, w, h):
        self.rounded(x-2,y-2,w+4,h+4,13,'','#122943',2)
        self.rounded(x,y,w,h,12,'#071125','#68bfd4')
        # A clipped vertical gradient gives the cards a glass-like depth.
        for py in range(2, int(h)-1, 3):
            inset = 1
            if py < 12:
                inset += 12-math.sqrt(max(0,144-(12-py)**2))
            elif py > h-12:
                inset += 12-math.sqrt(max(0,144-(py-(h-12))**2))
            self.rect(x+inset,y+py,w-2*inset,min(3,h-py-1),
                      mix('#12243e','#060c1c',py/h))

    def heading(self, y, title, x=28, width=230):
        self.text(x+width/2,y,title,10,'#d2e8f4',True,'center')

    def logo(self):
        c = self.canvas
        # Rainbow comet, drawn as vectors so the branding stays sharp on resize.
        for n,color in enumerate(('#45e9ff','#588aff','#975dff','#d671ff','#ffe08d')):
            c.create_polygon(49+n*14,38, 172,15, 66+n*12,41,
                             fill=color, outline='', tags='dynamic')
        c.create_line(172,5,172,27,fill='#d7faff',tags='dynamic')
        c.create_line(161,16,183,16,fill='#d7faff',tags='dynamic')
        self.text(25,47,'TFFERE',31,'#d4faff',True,italic=True,glow=True)
        self.text(143,110,'C O S M I C  T E T R I S',9,'#e4d9ff',True,'center',italic=True)

    def make_blocks(self):
        """Cache glossy sprites once per resize, rather than redraw every bevel."""
        self.block_images = {}
        size = max(1, round((CELL-4)*self.scale))
        for color in COLORS.values():
            image = tk.PhotoImage(master=self.root,width=size,height=size)
            rows = []
            for py in range(size):
                row = []
                y = py*(CELL-4)/size
                for px in range(size):
                    x = px*(CELL-4)/size
                    distances = (y,x,CELL-5-x,CELL-5-y)
                    edge = min(distances)
                    if edge < 6:
                        side = distances.index(edge)
                        target,amount = (('#ffffff',.57),('#ffffff',.25),
                                         ('#060919',.4),('#060919',.58))[side]
                        if y < 1:
                            target,amount = '#ffffff',.85
                    else:
                        target,amount = '#ffffff', .17*(1-y/(CELL-4))
                    row.append(mix(color,target,amount))
                rows.append('{'+' '.join(row)+'}')
            image.put(' '.join(rows))
            self.block_images[color] = image

    def block(self, x, y, color):
        self.rect(x+4,y+5,CELL-4,CELL-4,'#030713')
        self.canvas.create_image(x+2,y+2,image=self.block_images[color],
                                 anchor='nw',tags=('dynamic','block'))

    def draw(self):
        if not hasattr(self, 'background') or self.closed:
            return
        c, g = self.canvas, self.game
        c.delete('dynamic')
        self.draw_space()
        self.logo()
        self.panel(28,156,230,128)
        self.heading(180,'C U R R E N T   R U N')
        self.text(143,228,f'{g.score:06d}',30,'#b8f8ff',True,'center',glow=True)
        for x,label,value in ((28,'LEVEL',f'{g.level:02d}'),(151,'LINES',f'{g.lines:03d}')):
            self.panel(x,305,107,110)
            self.heading(329,label,x,107)
            self.text(x+53.5,375,value,29,'#bbf6ff',True,'center',glow=True)
        self.panel(28,437,230,104)
        self.heading(461,'N E X T   L E V E L')
        self.rounded(45,486,195,22,11,'#050e20','#82c8da')
        progress = (g.lines % 10)/10
        if progress:
            self.rounded(49,490,max(12,187*progress),14,7,'#0de4ef','#76f8ff')
        self.panel(28,563,230,105)
        self.heading(587,'S E S S I O N   B E S T')
        self.text(143,631,f'{self.best:06d}',27,'#c6f5ff',True,'center',glow=True)
        for name,y,caption in (('pause',723,'RESUME' if g.paused else 'PAUSE'),('restart',787,'RESTART')):
            self.panel(40,y,206,47)
            if self.hover == name:
                self.rounded(40,y,206,47,12,'','#8cf8ff',2)
            if name == 'pause':
                for dx in (0,7):
                    self.rect(69+dx,y+16,3,15,'#c9faff')
            else:
                c.create_arc(65,y+13,85,y+34,start=40,extent=285,style='arc',
                             outline='#c9faff',width=2,tags='dynamic')
                c.create_polygon(84,y+12,84,y+21,77,y+17,fill='#c9faff',outline='',tags='dynamic')
            self.text(158,y+23,caption,12,'#d4f7ff',True,'center')
        self.text(143,908,'F I N D  Y O U R  O R B I T .',8,'#ddd7fa',True,'center',italic=True)
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
                c.create_line(x-42, y-18, x, y, fill='#574184', width=2, tags='dynamic')
                c.create_line(x-18, y-8, x, y, fill='#c5b8ff', tags='dynamic')
                self.rect(x-1, y-1, 3, 3, '#f3eaff')
        # A distant saucer travels slowly across the upper half of the board.
        x = BOARD_X+35+(t*13) % (WIDTH*CELL-70)
        y = BOARD_Y+290+24*math.sin(t*.45)
        c.create_oval(x-5, y-7, x+5, y+3, fill='#334064', outline='#53668b', tags='dynamic')
        c.create_oval(x-15, y-1, x+15, y+6, fill='#30496d', outline='#b9b3ec', tags='dynamic')
        for dx in (-8, 0, 8):
            self.rect(x+dx-1, y+3, 2, 1, '#88a7bb')
        # A tiny rocket ascends well inside the right edge, behind the pieces.
        x = BOARD_X+WIDTH*CELL-55+8*math.sin(t*.4)
        y = BOARD_Y+HEIGHT*CELL-45-(t*23) % (HEIGHT*CELL-100)
        c.create_polygon(x,y-12, x-5,y-3, x-5,y+9, x+5,y+9, x+5,y-3,
                         fill='#b9c8df', outline='#d8f5ff', tags='dynamic')
        c.create_polygon(x-5,y+3, x-10,y+12, x-4,y+9,
                         fill='#5b8dbe', outline='', tags='dynamic')
        c.create_polygon(x+5,y+3, x+10,y+12, x+4,y+9,
                         fill='#5b8dbe', outline='', tags='dynamic')
        c.create_oval(x-2,y-2,x+2,y+2, fill='#32f0ff', outline='', tags='dynamic')
        c.create_polygon(x-3,y+10, x,y+19+3*math.sin(t*16), x+3,y+10,
                         fill='#bf6dff', outline='', tags='dynamic')

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
        if 40 <= x <= 246:
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
