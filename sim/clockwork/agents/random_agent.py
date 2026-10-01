"""Stage 0: uniformly random legal move."""
import random


class RandomAgent:
    name = "random"

    def __init__(self, seed=0):
        self.rng = random.Random(seed)

    def act(self, state, legal):
        return self.rng.choice(legal)
