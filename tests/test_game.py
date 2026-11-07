"""Gameplay regressions independent of the graphical display."""
import unittest
from tetris import Game, WIDTH, HEIGHT, SHAPES


class GameplayTests(unittest.TestCase):
    def test_seven_piece_bag(self):
        g = Game()
        g.bag = []
        self.assertEqual(set(g.pick() for _ in range(7)), set(SHAPES))

    def test_wall_collision(self):
        g = Game()
        while g.move(-1, 0):
            pass
        before = g.x
        self.assertFalse(g.move(-1, 0))
        self.assertEqual(g.x, before)
        self.assertTrue(g.valid(g.cells, g.x, g.y))

    def test_pause_blocks_all_piece_actions(self):
        g = Game()
        g.paused = True
        before = (g.x, g.y, g.cells, g.score, [r[:] for r in g.board])
        g.move(1, 0); g.rotate(); g.step(True); g.drop()
        self.assertEqual(before, (g.x, g.y, g.cells, g.score, g.board))

    def test_hard_drop_locks_four_cells_and_scores(self):
        g = Game()
        g.drop()
        self.assertEqual(sum(v is not None for row in g.board for v in row), 4)
        self.assertGreater(g.score, 0)

    def test_soft_drop_scores_one(self):
        g = Game()
        g.step(True)
        self.assertEqual((g.y, g.score), (1, 1))

    def test_single_clear(self):
        g = Game()
        g.board[-1] = ['T']*WIDTH
        for x in range(3, 7):
            g.board[-1][x] = None
        g.kind, g.cells, g.x, g.y = 'I', SHAPES['I'], 3, HEIGHT-2
        g.lock()
        self.assertEqual((g.lines, g.score, g.last_clear), (1, 100, [19]))
        self.assertFalse(any(any(row) for row in g.board))

    def test_tetris_and_level_transition(self):
        g = Game()
        g.lines = 6
        for y in range(16, 20):
            g.board[y] = ['T']*WIDTH
            g.board[y][5] = None
        g.kind, g.cells, g.x, g.y = 'I', ((2,0),(2,1),(2,2),(2,3)), 3, 16
        g.lock()
        self.assertEqual((g.lines, g.score, g.level), (10, 800, 2))

    def test_rotation_stays_valid_at_wall(self):
        g = Game()
        g.kind, g.cells = 'T', SHAPES['T']
        while g.move(-1, 0):
            pass
        for _ in range(4):
            g.rotate()
            self.assertTrue(g.valid(g.cells, g.x, g.y))

    def test_blocked_spawn_ends_game_and_restart_clears_it(self):
        g = Game()
        g.board[0] = ['T']*WIDTH
        g.board[1] = ['T']*WIDTH
        g.spawn()
        self.assertTrue(g.over)
        g.reset()
        self.assertFalse(g.over)
        self.assertEqual(g.score, 0)
        self.assertFalse(any(any(row) for row in g.board))


if __name__ == '__main__':
    unittest.main()
