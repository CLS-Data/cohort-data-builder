"""The clock the tool reads the time from; tests pass a fake one instead."""

import time


class SystemClock:
    """The real time, in seconds since the epoch."""

    def now(self) -> float:
        """The current time."""
        return time.time()
