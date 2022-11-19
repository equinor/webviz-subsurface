import time


class PerfTimer:
    def __init__(self) -> None:
        self._start_s = time.perf_counter()
        self._lap_s = self._start_s

    def elapsed_s(self) -> float:
        """Get the time elapsed since the start, in seconds"""
        return time.perf_counter() - self._start_s

    def elapsed_ms(self) -> int:
        """Get the time elapsed since the start, in milliseconds"""
        return int(1000 * self.elapsed_s())

    def lap_s(self) -> float:
        """Get elapsed time since last lap, in seconds"""
        time_now = time.perf_counter()
        elapsed = time_now - self._lap_s
        self._lap_s = time_now
        return elapsed

    def lap_ms(self) -> int:
        """Get elapsed time since last lap, in milliseconds"""
        return int(1000 * self.lap_s())
