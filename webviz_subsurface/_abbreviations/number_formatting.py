import json
import math
import pathlib
import warnings
from typing import List, Optional, Tuple, Union

_DATA_PATH = pathlib.Path(__file__).parent.absolute() / "abbreviation_data"

SI_PREFIXES = json.loads((_DATA_PATH / "si_prefixes.json").read_text())


def table_statistics_base() -> List[Tuple[str, dict]]:
    return [
        (
            i,
            {
                "type": "numeric",
                "format": {
                    "locale": {"symbol": ["", ""]},
                    "specifier": "$.4s",
                },
            },
        )
        if i != "Stddev"
        else (
            i,
            {
                "type": "numeric",
                "format": {
                    "locale": {"symbol": ["", ""]},
                    "specifier": "$.3s",
                },
            },
        )
        for i in ["Mean", "Stddev", "Minimum", "P90", "P10", "Maximum"]
    ]


def si_prefixed(
    number: float,
    number_format: str = "",
    unit: str = "",
    spaced: bool = True,
    locked_si_prefix: Optional[Union[str, int]] = None,
) -> str:
    """
    Formats a float as a string with SI-prefix and optionally a unit. Useful when you cannot/
    don't want to use the Dash d3-based formatting.
    Arguments:
    * `number` (float): Number to format
    * `number_format` (str): Format of the numeric part based on the Python Format Specification
    Mini-Language e.g. '.3g' for 3 significant digits, '.2f' for two decimals, or '.0f' for no
    decimals.
    * `unit` (str): String to append at the end as a unit
    * `spaced` (bool): Include a space between last numerical digit and SI-prefix.
    * `locked_si_prefix` (str or int): Lock the SI prefix to either a string (e.g. 'm' (milli) or
     'M' (mega)) or an integer which is the base 10 exponent (e.g. 3 for kilo, -3 for milli).
    """

    def number_formatter(number_base: float, si_prefix: str) -> str:
        return (
            f"{number_base:{number_format}} {si_prefix}{unit}"
            if spaced
            else f"{number_base:{number_format}}{si_prefix}{unit}"
        )

    if locked_si_prefix is not None:
        # Make sure locked_si_prefix is a string to avoid == issues
        locked_si_prefix = str(locked_si_prefix)

        if str(locked_si_prefix) == "" or locked_si_prefix == str(0):
            return number_formatter(number, "")

        for key, value in SI_PREFIXES.items():
            if locked_si_prefix == str(value) or locked_si_prefix == str(key):
                return number_formatter(number / (10 ** float(key)), value)
        # If we get further, an invalid si_prefix has been inputed, will throw warning, but
        # will continue and use non-locked prefix.
        warnings.warn(
            (
                f"An invalid locked_si_prefix={locked_si_prefix} was used. Ignoring the locked "
                "prefix and calculate instead."
            ),
            UserWarning,
        )
    # Calculate prefix based on value when not locked
    # Zero is a special case
    if number == 0:
        return number_formatter(0, SI_PREFIXES["0"])

    (exp_div_3, log10_rem) = divmod(math.log10(math.fabs(number)), 3)
    # Take log 10 and then mod 3 as we have one prefix per 10^3, the divisor*3 is then the exponent
    return (
        number_formatter(-(10**log10_rem), SI_PREFIXES[str(int(exp_div_3 * 3))])
        if (number < 0)
        else number_formatter(10**log10_rem, SI_PREFIXES[str(int(exp_div_3 * 3))])
    )
