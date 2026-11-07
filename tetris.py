"""A dependency-free Tetris game. Run with Python 3 and Tkinter."""
import random
import tkinter as tk

WIDTH, HEIGHT, CELL = 10, 20, 28
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


class App:
    def __init__(self, root):
        self.root, self.game = root, Game()
        root.title('Codex Tetris')
        root.resizable(False, False)
        self.canvas = tk.Canvas(root, width=WIDTH * CELL + 190,
                                height=HEIGHT * CELL, bg='#0f172a', highlightthickness=0)
        self.canvas.pack()
        root.bind('<KeyPress>', self.key)
        self.draw()
        self.timer = root.after(650, self.tick)

    def key(self, event):
        g, key = self.game, event.keysym.lower()
        if key == 'r':
            self.root.after_cancel(self.timer)
            g.reset()
            self.timer = self.root.after(650, self.tick)
        elif key == 'p' and not g.over:
            g.paused = not g.paused
        elif key == 'escape':
            self.root.destroy()
            return
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
        self.draw()

    def tick(self):
        self.game.step()
        self.draw()
        self.timer = self.root.after(max(80, 650 - (self.game.level - 1) * 50), self.tick)

    def block(self, x, y, color, ghost=False):
        self.canvas.create_rectangle(x + 1, y + 1, x + CELL - 1, y + CELL - 1,
                                     fill='' if ghost else color, outline=color, width=2)

    def draw(self):
        c, g = self.canvas, self.game
        c.delete('all')
        for y, row in enumerate(g.board):
            for x, kind in enumerate(row):
                self.block(x * CELL, y * CELL, COLORS[kind] if kind else '#1e293b')
        if not g.over:
            ghost_y = g.y
            while g.valid(g.cells, g.x, ghost_y + 1):
                ghost_y += 1
            for a, b in g.cells:
                self.block((g.x + a) * CELL, (ghost_y + b) * CELL, '#64748b', True)
            for a, b in g.cells:
                self.block((g.x + a) * CELL, (g.y + b) * CELL, COLORS[g.kind])
        sx = WIDTH * CELL + 18
        c.create_text(sx, 25, text='CODEX TETRIS', fill='#f8fafc', anchor='nw', font=('Arial', 14, 'bold'))
        c.create_text(sx, 75, text=f'Score  {g.score}\n\nLines  {g.lines}\n\nLevel  {g.level}\n\nNext',
                      fill='#e2e8f0', anchor='nw', font=('Arial', 12))
        for a, b in SHAPES[g.next]:
            self.block(sx + a * CELL, 250 + b * CELL, COLORS[g.next])
        c.create_text(sx, 350, text='← → / A D: move\n↑ / W: rotate\n↓ / S: soft drop\nSpace: hard drop\nP: pause\nR: restart\nEsc: quit',
                      fill='#94a3b8', anchor='nw', font=('Arial', 10), justify='left')
        if g.over or g.paused:
            c.create_rectangle(10, 230, WIDTH * CELL - 10, 320, fill='#0f172a', outline='#94a3b8')
            c.create_text(WIDTH * CELL // 2, 275,
                          text='GAME OVER\nPress R to restart' if g.over else 'PAUSED\nPress P to resume',
                          fill='white', font=('Arial', 18, 'bold'), justify='center')


if __name__ == '__main__':
    window = tk.Tk()
    App(window)
    window.mainloop()
