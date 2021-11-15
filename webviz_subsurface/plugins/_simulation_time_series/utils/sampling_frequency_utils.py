from ...._providers import Frequency

# TODO: Improve chek!
def frequency_leq(a: Frequency, b: Frequency) -> bool:
    """Check if frequency a is less or equal to frequency b"""
    frequencies = [
        Frequency.DAILY,
        Frequency.WEEKLY,
        Frequency.MONTHLY,
        Frequency.YEARLY,
    ]

    return frequencies.index(a) <= frequencies.index(b)


def frequency_gte(a: Frequency, b: Frequency) -> bool:
    """Check if frequency a is greater than or equal to frequency b"""
    frequencies = [
        Frequency.DAILY,
        Frequency.WEEKLY,
        Frequency.MONTHLY,
        Frequency.YEARLY,
    ]

    return frequencies.index(a) >= frequencies.index(b)