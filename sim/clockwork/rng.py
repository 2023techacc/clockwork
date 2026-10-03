"""Small seedable RNG (splitmix64). Its whole state is one integer, so cloning a game
state is cheap, which matters for search agents that clone thousands of times per move."""

_M = (1 << 64) - 1


class Rng:
    __slots__ = ("s",)

    def __init__(self, seed=0):
        self.seed(seed)

    def seed(self, x) -> None:
        if isinstance(x, float):
            x = int(x * (1 << 53))
        self.s = hash(x) & _M

    def copy(self) -> "Rng":
        r = Rng.__new__(Rng)
        r.s = self.s
        return r

    def _next(self) -> int:
        self.s = (self.s + 0x9E3779B97F4A7C15) & _M
        z = self.s
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _M
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _M
        return z ^ (z >> 31)

    def random(self) -> float:
        return (self._next() >> 11) / (1 << 53)

    def randrange(self, n: int) -> int:
        return self._next() % n

    def choice(self, seq):
        return seq[self._next() % len(seq)]

    def shuffle(self, x: list) -> None:
        for i in range(len(x) - 1, 0, -1):
            j = self._next() % (i + 1)
            x[i], x[j] = x[j], x[i]
