from typing import Any, Dict, List, Optional

import numpy as np
import xtgeo
from webviz_config.common_cache import CACHE

from webviz_subsurface._models import SurfaceSetModel
from webviz_subsurface._utils.colors import hex_to_rgba

from ...._utils.fanchart_plotting import (
    FanchartData,
    LowHighData,
    MinMaxData,
    get_fanchart_traces,
)


# pylint: disable=too-many-arguments
@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_plotly_trace_statistical_surface(
    surfaceset: SurfaceSetModel,
    fence_spec: np.ndarray,
    calculation: str,
    name: str,
    legendname: str,
    attribute: str,
    realizations: Optional[List[int]],
    color: str = "red",
    showlegend: bool = False,
    sampling: Optional[str] = "billinear",
) -> Dict[str, Any]:
    """Returns x,y values along a fence for a calculated surface"""
    surface = surfaceset.calculate_statistical_surface(
        name=name,
        attribute=attribute,
        calculation=calculation,
        realizations=realizations,
    )
    fencexy = get_surface_randomline(surface, fence_spec, sampling)
    line_style: Dict[str, Any] = {"width": 4}
    if calculation in ["Min", "Max"]:
        line_style.update({"dash": "dash"})
    return {
        "x": fencexy[:, 0],
        "y": fencexy[:, 1],
        "name": legendname,
        "legendgroup": name,
        "text": f"{legendname} {calculation}",
        "showlegend": showlegend,
        "hoverinfo": "y+x+text",
        "mode": "lines",
        "marker": {"color": hex_to_rgba(hex_string=color)},
        "line": line_style,
    }


# pylint: disable=too-many-arguments
@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_plotly_traces_uncertainty_envelope(
    surfaceset: SurfaceSetModel,
    fence_spec: np.ndarray,
    name: str,
    legendname: str,
    attribute: str,
    realizations: Optional[List[int]],
    color: str = "red",
    showlegend: bool = False,
    sampling: Optional[str] = "billinear",
) -> List:
    """Returns a set of plotly traces representing an uncertainty envelope
    for a surface"""
    stat_surfaces = {}
    for calculation in ["Min", "Max", "P10", "P90"]:
        stat_surfaces[calculation] = surfaceset.calculate_statistical_surface(
            name=name,
            attribute=attribute,
            calculation=calculation,
            realizations=realizations,
        ).get_randomline(fence_spec, sampling=sampling)

    data = FanchartData(
        samples=stat_surfaces["Min"][:, 0],
        low_high=LowHighData(
            low_data=stat_surfaces["P10"][:, 1],
            low_name="P10",
            high_data=stat_surfaces["P90"][:, 1],
            high_name="P90",
        ),
        minimum_maximum=MinMaxData(
            minimum=stat_surfaces["Min"][:, 1], maximum=stat_surfaces["Max"][:, 1]
        ),
    )
    return get_fanchart_traces(
        data=data,
        color=color,
        legend_group=name,
        legend_name=legendname,
        show_legend=showlegend,
        show_hoverinfo=False,
    )


# pylint: disable=too-many-arguments
@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_plotly_trace_realization_surface(
    surfaceset: SurfaceSetModel,
    fence_spec: np.ndarray,
    name: str,
    legendname: str,
    attribute: str,
    realization: int,
    showlegend: bool = False,
    sampling: Optional[str] = "billinear",
    color: str = "red",
) -> Dict[str, Any]:
    """Returns a plotly line trace for a surface"""
    surface = surfaceset.get_realization_surface(
        name=name, attribute=attribute, realization=realization
    )
    fencexy = get_surface_randomline(surface, fence_spec, sampling)
    return {
        "x": fencexy[:, 0],
        "y": fencexy[:, 1],
        "name": legendname,
        "legendgroup": name,
        "text": f"{legendname} realization: {realization}",
        "showlegend": showlegend,
        "hoverinfo": "y+x+text",
        "mode": "lines",
        "marker": {"color": hex_to_rgba(hex_string=color, opacity=0.5)},
    }


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_plotly_zonelog_trace(
    well: xtgeo.Well,
    zonelog: str,
) -> List[Dict]:
    """Zonetops are extracted from a zonelog and plotted as markers"""

    df = well.dataframe

    # Find zone transitions
    df["transitions"] = df[zonelog].diff()
    logrecord = well.get_logrecord(zonelog)
    traces = []
    for idx in range(0, df.shape[0] - 1):
        # Use current sample if moving upwards in stratigraphy
        # Use next sample if moving downwards in stratigraphy
        if df.iloc[idx + 1]["transitions"] < 0 or df.iloc[idx]["transitions"] > 0:
            traces.append(
                {
                    "x": [df.iloc[idx]["R_HLEN"]],
                    "y": [df.iloc[idx]["Z_TVDSS"]],
                    "marker": {"size": 10, "color": "red"},
                    "showlegend": False,
                    "hoverinfo": "y+name+text",
                    "text": "TVDSS",
                    "hoverlabel": {"namelength": -1},
                    "name": f"Zonetop: <br>{logrecord[df.iloc[idx][zonelog]]}",
                }
            )
    return traces


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_well_xyarray(well: xtgeo.Well) -> List:
    """Returns a copy of the x,y values representing the well fence"""
    dfr = well.dataframe
    zvals = dfr["Z_TVDSS"].values.copy()
    hvals = dfr["R_HLEN"].values.copy()
    return [hvals, zvals]


def get_plotly_trace_well_trajectory(well: xtgeo.Well) -> Dict[str, Any]:
    """Plot the trajectory as a black line"""
    xyarray = get_well_xyarray(well=well)

    return {
        "x": xyarray[0],
        "y": xyarray[1],
        "name": well.name,
        "hoverinfo": "name+text+y",
        "hoverlabel": {"namelength": -1},
        "text": "TVDSS",
        "marker": {"color": "black"},
    }


def get_surface_randomline(
    surface: xtgeo.RegularSurface,
    fence_spec: np.ndarray,
    sampling: Optional[str] = "billinear",
) -> np.ndarray:
    try:
        return surface.get_randomline(fence_spec, sampling=sampling)
    except TypeError:
        # Attempt to handle vertical wells
        fence_spec = np.insert(fence_spec, 0, fence_spec[0] - 10, axis=0)
        fence_spec = np.append(fence_spec, [fence_spec[-1] + 10], axis=0)
        return surface.get_randomline(fence_spec, sampling=sampling)
