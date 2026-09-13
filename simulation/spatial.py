# spatial hash grid. buckets the plate into cells so "whats near me"
# doesnt mean looping over every creature on screen.
# rebuilt from scratch every tick, its cheap enough (one dict insert each)

import math


class SpatialGrid:
    def __init__(self, width: int, height: int, cell: int = 64) -> None:
        self.width = width
        self.height = height
        self.cell = cell
        # 64px cells felt right, smaller and there are too many buckets
        self.cols = max(1, math.ceil(width / cell))
        self.rows = max(1, math.ceil(height / cell))
        self.cells: dict[tuple[int, int], list] = {}

    def rebuild(self, items: list) -> None:
        self.cells.clear()
        for it in items:
            key = (int(it.x) // self.cell, int(it.y) // self.cell)
            bucket = self.cells.get(key)
            if bucket is None:
                self.cells[key] = [it]
            else:
                bucket.append(it)

    def nearest(self, x: float, y: float, radius: float, accept=None):
        # closest thing in radius, or None. this is what the sensing code
        # calls. accept= is a filter so we can ask for "nearest PREY" etc
        c = self.cell
        # world wraps around so everything has to be measured the short way
        half_w, half_h = self.width / 2, self.height / 2
        best = None
        best_d2 = radius * radius
        x0 = int((x - radius) // c)
        x1 = int((x + radius) // c)
        y0 = int((y - radius) // c)
        y1 = int((y + radius) // c)

        for cx in range(x0, x1 + 1):
            for cy in range(y0, y1 + 1):
                # % wraps the cell index so it works across the edges
                bucket = self.cells.get((cx % self.cols, cy % self.rows))
                if not bucket:
                    continue
                for it in bucket:
                    dx = it.x - x
                    if dx > half_w:
                        dx -= self.width
                    elif dx < -half_w:
                        dx += self.width
                    if dx * dx > best_d2:
                        continue  # already too far in x, skip the rest
                    dy = it.y - y
                    if dy > half_h:
                        dy -= self.height
                    elif dy < -half_h:
                        dy += self.height
                    d2 = dx * dx + dy * dy
                    # shrink best_d2 as we go so later cells get rejected sooner
                    if d2 <= best_d2 and (accept is None or accept(it)):
                        best_d2 = d2
                        best = it
        return best

    def within(self, x: float, y: float, radius: float) -> list:
        # everything in radius, not just the closest one. mating uses this
        c = self.cell
        half_w, half_h = self.width / 2, self.height / 2
        r2 = radius * radius
        x0 = int((x - radius) // c)
        x1 = int((x + radius) // c)
        y0 = int((y - radius) // c)
        y1 = int((y + radius) // c)

        out = []
        for cx in range(x0, x1 + 1):
            for cy in range(y0, y1 + 1):
                bucket = self.cells.get((cx % self.cols, cy % self.rows))
                if not bucket:
                    continue
                for it in bucket:
                    dx = it.x - x
                    if dx > half_w:
                        dx -= self.width
                    elif dx < -half_w:
                        dx += self.width
                    if dx * dx > r2:
                        continue
                    dy = it.y - y
                    if dy > half_h:
                        dy -= self.height
                    elif dy < -half_h:
                        dy += self.height
                    if dx * dx + dy * dy <= r2:
                        out.append(it)
        return out
