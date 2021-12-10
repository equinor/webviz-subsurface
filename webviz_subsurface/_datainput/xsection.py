from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import xtgeo
from numpy import ma
from plotly.subplots import make_subplots

from .._utils.colors import hex_to_rgba_str


class XSectionFigure:
    """Class for plotting a cross-section of a well.

    Args:
        zmin (float): Upper level of the plot (top Y axis).
        zmax (float): Lower level of the plot (bottom Y axis).
        well (Well): XTGeo well object.
        surfaces (list): List of XTGeo RegularSurface objects
        surfacenames (list): List of surface names (str) for legend
        cube (Cube): A XTGeo Cube instance
        grid (Grid): A XTGeo Grid instance
        gridproperty (GridProperty): A XTGeo GridProperty instance

    """

    # pylint: disable=too-many-instance-attributes, too-many-arguments
    def __init__(
        self,
        zmin: Optional[float] = None,
        zmax: Optional[float] = None,
        well: Optional[xtgeo.Well] = None,
        surfaces: Optional[List[xtgeo.RegularSurface]] = None,
        sampling: int = 5,
        nextend: int = 5,
        zonelogshift: int = 0,
        surfacenames: Optional[List[str]] = None,
        surfacecolors: Optional[List[str]] = None,
        cube: Optional[xtgeo.Cube] = None,
        grid: Optional[xtgeo.Grid] = None,
        gridproperty: Optional[xtgeo.GridProperty] = None,
        zunit: str = "",
        show_marginal: bool = False,
    ) -> None:

        self._data: List[Any] = []
        self._figure = make_subplots(
            rows=2 if show_marginal else 1,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0,
            row_heights=[0.05, 0.95] if show_marginal else [1],
        )
        if well:
            self._zmin = zmin if zmin else well.dataframe["Z_TVDSS"].min()
            self._zmax = zmax if zmax else well.dataframe["Z_TVDSS"].max()
        self._well = well
        self._nextend = nextend
        self._sampling = sampling
        self._surfaces = surfaces
        self._surfacenames = surfacenames
        self._surfacecolors = (
            surfacecolors
            if surfacecolors is not None
            else [
                "#1f77b4",  # muted blue
                "#ff7f0e",  # safety orange
                "#2ca02c",  # cooked asparagus green
                "#d62728",  # brick red
                "#9467bd",  # muted purple
                "#8c564b",  # chestnut brown
                "#e377c2",  # raspberry yogurt pink
                "#7f7f7f",  # middle gray
                "#bcbd22",  # curry yellow-green
                "#17becf",  # blue-teal
            ]
        )
        self.zunit = zunit
        self.show_marginal = show_marginal
        self.main_trace_row = 2 if show_marginal else 1
        self._cube = cube
        self._grid = grid
        self._gridproperty = gridproperty
        self._zonelogshift = zonelogshift

        self._fence = None

    @property
    def data(self) -> Any:
        """The Plotly figure traces"""
        # TODO: According to
        # https://plotly.com/python-api-reference/generated/plotly.graph_objects.Figure.html
        # this can return very different types.
        return self._figure.data

    @property
    def layout(self) -> Dict[str, Any]:
        """The Plotly figure layout"""
        _layout = self._figure.layout
        yax = "yaxis2" if self.show_marginal else "yaxis"
        _layout.update(
            {
                "height": 800,
                # "margin": {"t":300},
                "xaxis2": {
                    "showgrid": False,
                    "title": "Distance from well",
                    "zeroline": False,
                },
                yax: {
                    "range": [self._zmax, self._zmin],
                    "showgrid": False,
                    "title": "Depth",
                    "zeroline": False,
                },
                "legend": {"traceorder": "normal"},
                "hovermode": "x",
            }
        )

        return _layout

    @property
    def fence(self) -> Optional[np.ndarray]:
        """Set or get the fence spesification"""
        if self._fence is None:
            if self._well is not None:
                wfence = self._well.get_fence_polyline(
                    sampling=self._sampling, nextend=self._nextend, tvdmin=self._zmin
                )
                self._fence = wfence

                if wfence is False:
                    self._fence = None
            else:
                raise ValueError("Input well is None")  # should be more flexible
        return self._fence

    def plot_well(
        self,
        zonelogname: Optional[str] = "ZONELOG",
        facieslogname: Optional[str] = None,
        marginal_log: Optional[str] = None,
        zonemin: int = 0,
    ) -> None:
        """Input an XTGeo Well object and plot it."""
        well = self._well

        # reduce the well data by Pandas operations
        dfr = well.dataframe
        well.dataframe = dfr[dfr["Z_TVDSS"] > self._zmin]

        # Create a relative XYLENGTH vector (0.0 where well starts)
        well.create_relative_hlen()

        dfr = well.dataframe

        # get the well trajectory (numpies) as copy
        zvals = dfr["Z_TVDSS"].values.copy()
        hvals = dfr["R_HLEN"].values.copy()
        self._plot_well_traj(zvals, hvals)
        if zonelogname:
            self._plot_well_zlog(dfr, zvals, hvals, zonelogname, zonemin)

        # plot the facies, if any, behind the trajectory; ie. first or second
        if facieslogname:
            self._plot_well_faclog(dfr, zvals, hvals, facieslogname)
        if marginal_log:
            self._plot_marginal_log(dfr, zvals, hvals, marginal_log)

    def _plot_well_traj(self, zvals: np.ndarray, hvals: np.ndarray) -> None:
        """Plot the trajectory as a black line"""

        zvals_copy = ma.masked_where(zvals < self._zmin, zvals)
        hvals_copy = ma.masked_where(zvals < self._zmin, hvals)

        self._figure.add_trace(
            {
                "x": hvals_copy,
                "y": zvals_copy,
                "name": self._well.name,
                "marker": {"color": "black"},
            },
            self.main_trace_row,
            1,
        )

        # ax.plot(hvals_copy, zvals_copy, linewidth=6, c="black")

    # pylint: disable-too-many-locals
    def _plot_well_zlog(
        self,
        df: pd.DataFrame,
        zvals: np.ndarray,
        hvals: np.ndarray,
        zonelogname: str,
        zomin: int = -999,
    ) -> None:
        """Plot the zone log as colored segments."""

        if zonelogname not in df.columns:
            return
        zonevals = df[zonelogname].values
        zomin = (
            zomin if zomin >= int(df[zonelogname].min()) else int(df[zonelogname].min())
        )
        zomax = int(df[zonelogname].max())

        # To prevent gaps in the zonelog it is necessary to duplicate each zone transition
        zone_transitions = np.where(zonevals[:-1] != zonevals[1:])
        for transition in zone_transitions:
            try:
                zvals = np.insert(zvals, transition, zvals[transition + 1])
                hvals = np.insert(hvals, transition, hvals[transition + 1])
                zonevals = np.insert(zonevals, transition, zonevals[transition])
            except IndexError:
                pass

        for i, zone in enumerate(range(zomin, zomax + 1)):
            zvals_copy = ma.masked_where(zonevals != zone, zvals)
            hvals_copy = ma.masked_where(zonevals != zone, hvals)
            color = self._surfacecolors[i % len(self._surfacecolors)]
            self._figure.add_trace(
                {
                    "x": hvals_copy.compressed(),
                    "y": zvals_copy.compressed(),
                    "line": {"width": 10, "color": color},
                    "fillcolor": color,
                    "marker": {"opacity": 0.5},
                    "showlegend": False,
                    "name": f"Zone: {zone}",
                },
                self.main_trace_row,
                1,
            )

    def _plot_well_faclog(
        self, df: pd.DataFrame, zvals: np.ndarray, hvals: np.ndarray, facieslogname: str
    ) -> None:
        """Plot the facies log as colored segments.

        Args:
            df (dataframe): The Well dataframe.
            zvals (ndarray): The numpy Z TVD array.
            hvals (ndarray): The numpy Length  array.
            facieslogname (str): name of the facies log.
        """

        if facieslogname not in df.columns:
            return

        frecord = self._well.get_logrecord(facieslogname)
        frecord = {val: fname for val, fname in frecord.items() if val >= 0}

        faciesvalues = df[facieslogname].values

        for fcc in frecord:

            zvals_copy = ma.masked_where(faciesvalues != fcc, zvals)
            hvals_copy = ma.masked_where(faciesvalues != fcc, hvals)

            self._figure.add_trace(
                {
                    "x": hvals_copy,
                    "y": zvals_copy,
                    "line": {"width": 5},
                    "connectgaps": True,
                },
                self.main_trace_row,
                1,
            )

        # self._drawlegend(ax, bba, title="Facies")

    def _plot_marginal_log(
        self,
        df: pd.DataFrame,
        zvals: np.ndarray,
        hvals: np.ndarray,
        logname: str,
        row: int = 1,
    ) -> None:
        """Plot a marginal log above main plot"""
        if logname in df.columns:
            self._figure.add_trace(
                {
                    "mode": "lines",
                    "fill": "tozeroy",
                    "x": hvals,
                    "y": df[logname],
                    "name": logname,
                    "hovertext": [
                        f"TVD: {zvals[i]}<br>" f"{logname}: {list(df[logname])[i]}<br>"
                        for i, _ in enumerate(hvals)
                    ],
                    "hoverinfo": "text",
                    "line": {"color": self._surfacecolors[0]},
                    "fillcolor": self._surfacecolors[0],
                },
                row,
                1,
            )

    # pylint: disable=too-many-locals, unused-argument
    def plot_cube(
        self,
        cube: xtgeo.Cube = None,
        vmin: Optional[float] = None,
        vmax: Optional[float] = None,
        alpha: float = 0.7,
        interpolation: str = "gaussian",
        sampling: str = "nearest",
        name: str = "seismic",
    ) -> None:
        """Plot a cube backdrop.

        Args:
            vmin (float): Minimum value in plot.
            vmax (float); Maximum value in plot
            alpha (float): Alpah blending number beween 0 and 1.
            interpolation (str): Interpolation for plotting, cf. matplotlib
                documentation on this. Also gaussianN is allowed, where
                N = 1..9.
            sampling (str): 'nearest' (default) or 'trilinear' (more precise)

        Raises:
            ValueError: No cube is loaded

        """
        if cube:
            self._cube = cube
        if self._cube is None:
            raise ValueError("Ask for plot cube, but noe cube is loaded")

        zinc = self._cube.zinc / 2.0

        zvalsv = self._cube.get_randomline(
            self.fence,
            zmin=self._zmin,
            zmax=self._zmax,
            zincrement=zinc,
            sampling=sampling,
        )

        xmin, xmax, ymin, ymax, arr = zvalsv
        x_inc = (xmax - xmin) / arr.shape[1]
        y_inc = (ymax - ymin) / arr.shape[0]
        # if vmin is not None or vmax is not None:
        #     arr = np.clip(arr, vmin, vmax)

        self._figure.add_trace(
            {
                "type": "heatmap",
                "z": arr,
                "x0": xmin,
                # "xmax": xmax,
                "dx": x_inc,
                "y0": ymin,
                # "ymax": ymax,
                "dy": y_inc,
                "zsmooth": "best",
                "showscale": False,
                "name": name
                # "colorscale": colors,
            },
            self.main_trace_row,
            1,
        )

    # pylint: disable=unused-argument
    def plot_grid3d(
        self,
        vmin: Optional[float] = None,
        vmax: Optional[float] = None,
        alpha: float = 0.7,
    ) -> None:
        """Plot a sampled grid with gridproperty backdrop.

        Args:
            vmin (float): Minimum value in plot.
            vmax (float); Maximum value in plot
            alpha (float): Alpha blending number beween 0 and 1.

        Raises:
            ValueError: No grid or gridproperty is loaded

        """
        if self._grid is None or self._gridproperty is None:
            raise ValueError("Ask for plot of grid, but no grid is loaded")

        zinc = 0.5  # tmp

        zvalsv = self._grid.get_randomline(
            self.fence,
            self._gridproperty,
            zmin=self._zmin,
            zmax=self._zmax,
            zincrement=zinc,
        )

        xmin, xmax, ymin, ymax, arr = zvalsv
        x_inc = (xmax - xmin) / arr.shape[1]
        y_inc = (ymax - ymin) / arr.shape[0]
        # if vmin is not None or vmax is not None:
        #     arr = np.clip(arr, vmin, vmax)

        self._figure.add_trace(
            {
                "type": "heatmap",
                "z": arr,
                "x0": xmin,
                "xmax": xmax,
                "dx": x_inc,
                "y0": ymin,
                "ymax": ymax,
                "dy": y_inc,
                "zsmooth": "best",
                "showscale": False,
                # "colorscale": colors,
            },
            self.main_trace_row,
            1,
        )

    def plot_surfaces(
        self,
        fill: bool = False,
        surfaces: List[xtgeo.RegularSurface] = None,
        surfacenames: Optional[List[str]] = None,
    ) -> None:

        """Input a surface list (ordered from top to base) , and plot them."""

        # ax, bba = self._currentax(axisname=axisname)

        # either use surfaces from __init__, or override with surfaces
        # specified here

        if surfaces and surfacenames and len(surfaces) == len(surfacenames):
            for i, surface in enumerate(surfaces):

                hfence1 = surface.get_randomline(self.fence).copy()
                self._figure.add_trace(
                    {
                        "type": "scatter",
                        "mode": "lines",
                        "fill": "tonexty" if i != 0 and fill else None,
                        "y": hfence1[:, 1],
                        "x": hfence1[:, 0],
                        "name": surfacenames[i],
                        # "marker": {"color": s_color},
                    },
                    self.main_trace_row,
                    1,
                )

    def plot_statistical_surface(
        self,
        statistical_surfaces: Dict[str, xtgeo.RegularSurface],
        name: str,
        fill: bool = False,
    ) -> None:
        """Plot statistical surfaces (p10/p90/min/max/mean) as fanchart

        Args:
            statistical_surfaces: Dict of xtgeo surfaces
            name: Name of surface (e.g. horizon name)
            fill: Toggles fill between surfaces
        """

        color = self._surfacecolors[
            self._surfacenames.index(name) % len(self._surfacecolors)  # type: ignore[union-attr]
        ]

        fill_color = hex_to_rgba_str(color, 0.3)
        line_color = hex_to_rgba_str(color, 1)

        # Extract surface values along well fence
        x_values = statistical_surfaces["mean"].get_randomline(self.fence).copy()[:, 0]
        stat = {
            key: statistical_surfaces[key].get_randomline(self.fence).copy()[:, 1]
            for key in ["maximum", "minimum", "p90", "p10", "mean", "stddev"]
        }

        # Maximum trace (contains hoverinfo)
        self._figure.add_trace(
            {
                "name": name,
                "y": stat["maximum"],
                "x": x_values,
                "mode": "lines",
                "hovertext": [
                    f"Minimum: {stat['minimum'][i]:.2f} {self.zunit}<br>"
                    f"P10: {stat['p10'][i]:.2f} {self.zunit}<br>"
                    f"Mean: {stat['mean'][i]:.2f} {self.zunit}<br>"
                    f"P90: {stat['p90'][i]:.2f} {self.zunit}<br>"
                    f"Maximum: {stat['maximum'][i]:.2f} {self.zunit}<br>"
                    f"Std.Dev: {stat['stddev'][i]:.2f} {self.zunit}"
                    for i, _ in enumerate(x_values)
                ],
                "hoverinfo": "text+name",
                "line": {"width": 0 if fill else 1, "color": line_color},
                "legendgroup": name,
                "showlegend": False,
            },
            self.main_trace_row,
            1,
        )
        # P10 trace
        self._figure.add_trace(
            {
                "name": name,
                "y": stat["p10"],
                "x": x_values,
                "mode": "lines",
                "hoverinfo": "skip",
                "fill": "tonexty" if fill else None,
                "fillcolor": fill_color,
                "line": {"width": 0 if fill else 1, "color": line_color},
                "legendgroup": name,
                "showlegend": False,
            },
            self.main_trace_row,
            1,
        )
        # Mean trace
        self._figure.add_trace(
            {
                "name": name,
                "y": stat["mean"],
                "x": x_values,
                "mode": "lines",
                "hoverinfo": "skip",
                "fill": "tonexty" if fill else None,
                "fillcolor": fill_color,
                "line": {"color": line_color},
                "legendgroup": name,
                "showlegend": True,
            },
            self.main_trace_row,
            1,
        )
        # P90 trace
        self._figure.add_trace(
            {
                "name": name,
                "y": stat["p90"],
                "x": x_values,
                "mode": "lines",
                "hoverinfo": "skip",
                "fill": "tonexty" if fill else None,
                "fillcolor": fill_color,
                "line": {"width": 0 if fill else 1, "color": line_color},
                "legendgroup": name,
                "showlegend": False,
            },
            self.main_trace_row,
            1,
        )
        # Minimum trace
        self._figure.add_trace(
            {
                "name": name,
                "y": stat["minimum"],
                "x": x_values,
                "mode": "lines",
                "hoverinfo": "skip",
                "fill": "tonexty" if fill else None,
                "fillcolor": fill_color,
                "line": {"width": 0 if fill else 1, "color": line_color},
                "legendgroup": name,
                "showlegend": False,
            },
            self.main_trace_row,
            1,
        )
