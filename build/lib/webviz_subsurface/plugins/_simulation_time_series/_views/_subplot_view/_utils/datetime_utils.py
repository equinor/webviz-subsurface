import datetime

# DOCS: https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior


def from_str(date_str: str) -> datetime.datetime:
    return datetime.datetime.strptime(date_str, "%Y-%m-%d")


def to_str(date: datetime.datetime) -> str:
    if date.hour != 0 or date.minute != 0 or date.second != 0 or date.microsecond != 0:
        raise ValueError(
            f"Invalid date resolution, expected no data for hour, minute, second"
            f" or microsecond for {str(date)}"
        )
    return date.strftime("%Y-%m-%d")
