"""Spatial hash grid: fast neighbor queries on the toroidal world.

Rebuilt once per tick (cheap: one dict insert per item). Queries scan
only the cells a circle overlaps, so cost is independent of population
size for small radii — this is what makes local mating (and later,
predation) affordable at large populations.
"""

import math


class SpatialGrid:
    def __init__(self, width: int, height: int, cell: int = 64) -> None:
        self.width = width
        self.height = height
        self.cell = cell
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
        """The closest item within `radius` of (x, y), or None.

        Toroidal like `within`, but returns one item instead of a list —
        which is what sensing wants, and it allocates nothing. `accept`
        optionally filters candidates (e.g. "is this actually prey?").
        """
        c = self.cell
        half_w, half_h = self.width / 2, self.height / 2
        best = None
        best_d2 = radius * radius
        x0 = int((x - radius) // c)
        x1 = int((x + radius) // c)
        y0 = int((y - radius) // c)
        y1 = int((y + radius) // c)

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
                    if dx * dx > best_d2:
                        continue  # early reject on x alone
                    dy = it.y - y
                    if dy > half_h:
                        dy -= self.height
                    elif dy < -half_h:
                        dy += self.height
                    d2 = dx * dx + dy * dy
                    # Tightening `best_d2` as we go prunes later candidates.
                    if d2 <= best_d2 and (accept is None or accept(it)):
                        best_d2 = d2
                        best = it
        return best

    def within(self, x: float, y: float, radius: float) -> list:
        """Items within `radius` of (x, y), toroidal-aware."""
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
