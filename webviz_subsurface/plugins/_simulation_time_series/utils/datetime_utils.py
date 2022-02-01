import datetime

# DOCS: https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior


def from_str(date_str: str) -> datetime.datetime:
    return datetime.datetime.strptime(date_str, "%Y-%m-%d")


def to_str(date: datetime.datetime) -> str:
    if (
        date.hour != 0
        and date.minute != 0
        and date.second != 0
        and date.microsecond != 0
    ):
        raise ValueError(
            f"Invalid date resolution, expected no data for hour, minute, second"
            f" or microsecond for {str(date)}"
        )
    return date.strftime("%Y-%m-%d")


# from dateutil import parser

# NOTE: ADD "python-dateutil>=2.8.2", to setup.py if so!

# def from_str(date_str: str) -> datetime.datetime:
#     return parser.parse(date_str)


# def to_str(date: datetime.datetime) -> str:
#     str()
#     if (
#         date.hour != 0
#         and date.minute != 0
#         and date.second != 0
#         and date.microsecond != 0
#     ):
#         raise ValueError(
#             f"Invalid date resolution, expected no data finer than day for {str(date)}"
#         )
#     return date.strftime("%m-%d-%y")
