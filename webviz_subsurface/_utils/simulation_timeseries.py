import warnings
from typing import Optional

import pandas as pd


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

    if smry_meta is None:
        return line_shape_fallback
    try:
        if smry_meta.is_rate[vector]:
            return "vh"
        if smry_meta.is_total[vector]:
            return "linear"
    except (AttributeError, KeyError):
        pass
    return line_shape_fallback
