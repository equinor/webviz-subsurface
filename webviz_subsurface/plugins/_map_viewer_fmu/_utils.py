import math


def round_to_significant(val: float, sig: int = 2) -> float:
    return round(val, sig - int(math.floor(math.log10(abs(val)))) - 1)
