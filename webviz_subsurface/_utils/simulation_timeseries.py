import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import yaml
from webviz_config.utils import terminal_colors


def set_simulation_line_shape_fallback(line_shape_fallback: str) -> str:
    """
    Defines a Plotly line_shape to use if a vector is not thought to be a rate or a total.
    """
    line_shape_fallback = line_shape_fallback.lower()
    if line_shape_fallback in ("backfilled", "backfill"):
        return "vh"
    if line_shape_fallback in ["hv", "vh", "hvh", "vhv", "spline", "linear"]:
        return line_shape_fallback
    warnings.warn(
        f"{line_shape_fallback}, is not a valid line_shape option, will use linear."
    )
    return "linear"


def get_simulation_line_shape(
    line_shape_fallback: str, vector: str, smry_meta: Optional[pd.DataFrame] = None
) -> str:
    """Get simulation time series line shape, smry_meta is a pd.DataFrame on the format given
    by `load_smry_meta` in `../_datainput/fmu_input.py`.
    """
    if vector.startswith("AVG_") or vector.startswith("INTVL_"):
        # These custom calculated vectors are valid forwards in time.
        return "hv"

    if smry_meta is None:
        return line_shape_fallback
    try:
        if smry_meta.is_rate[vector]:
            # Eclipse rate vectors are valid backwards in time.
            return "vh"
        if smry_meta.is_total[vector]:
            return "linear"
    except (AttributeError, KeyError):
        pass
    return line_shape_fallback


def calc_series_statistics(
    df: pd.DataFrame, vectors: list, refaxis: str = "DATE"
) -> pd.DataFrame:
    """Calculate statistics for given vectors over the ensembles
    refaxis is used if another column than DATE should be used to groupby.
    """
    # Invert p10 and p90 due to oil industry convention.
    def p10(x: List[float]) -> np.floating:
        return np.nanpercentile(x, q=90)

    def p90(x: List[float]) -> np.floating:
        return np.nanpercentile(x, q=10)

    def p50(x: List[float]) -> np.floating:
        return np.nanpercentile(x, q=50)

    # Calculate statistics, ignoring NaNs.
    stat_df = (
        df[["ENSEMBLE", refaxis] + vectors]
        .groupby(["ENSEMBLE", refaxis])
        .agg([np.nanmean, np.nanmin, np.nanmax, p10, p90, p50])
        .reset_index(level=["ENSEMBLE", refaxis], col_level=1)
    )
    # Rename nanmin, nanmax and nanmean to min, max and mean.
    col_stat_label_map = {
        "nanmin": "min",
        "nanmax": "max",
        "nanmean": "mean",
        "p10": "high_p10",
        "p90": "low_p90",
        "p50": "p50",
    }
    stat_df.rename(columns=col_stat_label_map, level=1, inplace=True)

    return stat_df


def add_statistics_traces(
    ens_stat_df: pd.DataFrame,
    vector: str,
    stat_options: List[str],
    color: str,
    legend_group: str,
    line_shape: str,
    refaxis: str = "DATE",
    hovertemplate: str = "(%{x}, %{y})<br>",
) -> List[Dict[str, Any]]:
    """Renders a statistical lines for each vector"""
    traces = []
    for i, opt in enumerate(stat_options):
        if opt == "Mean":
            traces.append(
                {
                    "name": legend_group,
                    "hovertemplate": hovertemplate + "Mean",
                    "x": ens_stat_df[("", refaxis)],
                    "y": ens_stat_df[(vector, "mean")],
                    "mode": "lines",
                    "line": {"color": color, "shape": line_shape, "width": 3},
                    "legendgroup": legend_group,
                    "showlegend": True,
                }
            )
        if opt == "P10 (high)":
            traces.append(
                {
                    "name": legend_group,
                    "hovertemplate": hovertemplate + "P10",
                    "x": ens_stat_df[("", refaxis)],
                    "y": ens_stat_df[(vector, "high_p10")],
                    "mode": "lines",
                    "line": {"color": color, "shape": line_shape, "dash": "dashdot"},
                    "legendgroup": legend_group,
                    "showlegend": False if "Mean" in stat_options else i == 0,
                }
            )
        if opt == "P90 (low)":
            traces.append(
                {
                    "name": legend_group,
                    "hovertemplate": hovertemplate + "P90",
                    "x": ens_stat_df[("", refaxis)],
                    "y": ens_stat_df[(vector, "low_p90")],
                    "mode": "lines",
                    "line": {"color": color, "shape": line_shape, "dash": "dashdot"},
                    "legendgroup": legend_group,
                    "showlegend": False if "Mean" in stat_options else i == 0,
                }
            )
        if opt == "P50 (median)":
            traces.append(
                {
                    "name": legend_group,
                    "hovertemplate": hovertemplate + "P50",
                    "x": ens_stat_df[("", refaxis)],
                    "y": ens_stat_df[(vector, "p50")],
                    "mode": "lines",
                    "line": {
                        "color": color,
                        "shape": line_shape,
                        "dash": "dot",
                        "width": 3,
                    },
                    "legendgroup": legend_group,
                    "showlegend": False if "Mean" in stat_options else i == 0,
                }
            )
        if opt == "Maximum":
            traces.append(
                {
                    "name": legend_group,
                    "hovertemplate": hovertemplate + "Maximum",
                    "x": ens_stat_df[("", refaxis)],
                    "y": ens_stat_df[(vector, "max")],
                    "mode": "lines",
                    "line": {
                        "color": color,
                        "shape": line_shape,
                        "dash": "longdash",
                        "width": 1.5,
                    },
                    "legendgroup": legend_group,
                    "showlegend": False if "Mean" in stat_options else i == 0,
                }
            )
        if opt == "Minimum":
            traces.append(
                {
                    "name": legend_group,
                    "hovertemplate": hovertemplate + "Minimum",
                    "x": ens_stat_df[("", refaxis)],
                    "y": ens_stat_df[(vector, "min")],
                    "mode": "lines",
                    "line": {
                        "color": color,
                        "shape": line_shape,
                        "dash": "longdash",
                        "width": 1.5,
                    },
                    "legendgroup": legend_group,
                    "showlegend": False if "Mean" in stat_options else i == 0,
                }
            )
    return traces


def render_hovertemplate(vector: str, interval: Optional[str]) -> str:
    if vector.startswith(("AVG_", "INTVL_")) and interval is not None:
        if interval == "daily":
            return "(%{x|%b} %{x|%-d}, %{x|%Y}, %{y})<br>"
        if interval == "monthly":
            return "(%{x|%b} %{x|%Y}, %{y})<br>"
        if interval == "yearly":
            return "(%{x|%Y}, %{y})<br>"
        raise ValueError(f"Interval {interval} is not supported.")
    return "(%{x}, %{y})<br>"  # Plotly's default behavior


def date_to_interval_conversion(
    date: Optional[str], vector: str, interval: str, as_date: bool = False
) -> Optional[str]:
    """Converts a date on form YYYY-MM-DD to an interval 'date' if the
    vector is a vector that is calculated from cumulatives (AVG_ or INTVL_).
    If as_date=True, the date returned will be the the first date of the interval
    (independent of which date in the interval the input is),
    if not, the 'date' returned will be the common basis for the interval,
    e.g. YYYY-MM-DD for daily, YYYY-MM for monthly and YYYY for yearly.

    The input date must be a date that can be reduced to the interval date by simply
    removing terms, e.g. is both 2001-05-16 and 2001-05-01 ok for monthly and will return
    2001-05.
    """
    if date is None:
        return date
    if vector.startswith(("AVG_", "INTVL_")):
        if interval == "monthly":
            date = "-".join(date.split("-")[0:2]) + ("-01" if as_date else "")
        if interval == "yearly":
            date = date.split("-")[0] + ("-01-01" if as_date else "")
    return date


# pylint: disable=too-many-branches
def check_and_format_observations(obsfile: Path) -> dict:
    with open(obsfile, "r") as stream:
        try:
            obsfile_data = yaml.safe_load(stream)
        except yaml.MarkedYAMLError as excep:
            extra_info = (
                f"There is something wrong in the configuration file {obsfile}. "
            )

            if (problem_mark := getattr(excep, "problem_mark", None)) is not None:
                extra_info += (
                    "The typo is probably somewhere around "
                    f"line {problem_mark.line + 1}."
                )

            raise type(excep)(
                f"{excep}. {terminal_colors.RED}{terminal_colors.BOLD}"
                f"{extra_info}{terminal_colors.END}"
            ).with_traceback(sys.exc_info()[2])

        try:
            obslist = obsfile_data.pop("smry")
        except KeyError as exc:
            raise KeyError(
                "The observation file lacks a `smry` section, which is mandatory for observations "
                "to work with this plugin."
            ) from exc
        except TypeError as exc:
            raise TypeError(
                "The observation file's othermost level must be a dictionary, while the input "
                f"file's outermost level is of type {type(obsfile_data)}."
            ) from exc
        if not isinstance(obslist, list):
            raise TypeError(
                "The observation file's smry section must be formatted as a list of dictionaries."
            )
        observations: dict = {}

        # pylint: disable=too-many-nested-blocks
        for item in obslist:
            if isinstance(item, dict):
                if "key" not in item:
                    raise KeyError(
                        "Missing mandatory element `key` in the observation file's smry section "
                        f"for the entry {item}."
                    )
                if "observations" not in item:
                    raise KeyError(
                        "Missing mandatory element `observations` in the observation file's smry "
                        f"section the entry {item}."
                    )
                key = item.pop("key")
                if isinstance(item["observations"], list):
                    for obs in item["observations"]:
                        if isinstance(obs, dict):
                            if "value" in obs and "date" in obs:
                                # Silently ignoring missing error, as the observation is still
                                # plotted as a point as long as "value" and "date"
                                # are present.
                                pass
                            else:
                                raise KeyError(
                                    f"Missing value and/or date for smry observation {obs} "
                                    f"under key {key} in smry section of observation file."
                                )
                        else:
                            raise TypeError(
                                f"Observation not formatted as dictionary in smry section of "
                                f"observation file. Check key: {key}, observation: {obs}."
                            )
                else:
                    raise KeyError(
                        "A smry observation must at least contain a `value` and a `date`."
                        f"Check at least key: {key}, observation: {item} in the observation "
                        f"file."
                    )
                observations[key] = item
            else:
                raise TypeError(
                    f"{item} in the observation file's smry section is not a dictionary."
                )
    return observations
