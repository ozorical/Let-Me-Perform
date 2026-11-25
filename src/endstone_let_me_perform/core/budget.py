import time


class Budget:
    __slots__ = ("_deadline",)

    def __init__(self, milliseconds: float):
        self._deadline = time.perf_counter() + milliseconds / 1000.0

    def spent(self) -> bool:
        return time.perf_counter() >= self._deadline
