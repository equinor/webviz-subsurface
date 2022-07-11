from typing import List

from dash import callback, Input, Output
from dash.exceptions import PreventUpdate
import numpy as np
import pandas as pd
from webviz_config import WebvizSettings
from webviz_config.webviz_plugin_subclasses import ViewABC

from ..._plugin_ids import PlugInIDs
from ....._utils.fanchart_plotting import (
    FanchartData,
    FreeLineData,
    get_fanchart_traces,
    LowHighData,
    MinMaxData,
)
from ...view_elements import Graph


class RelpermCappres(ViewABC):
    """View for the Relative Permeability plugin"""

    class IDs:
        # pylint: disable=too-few-public-methods
        RELATIVE_PERMEABILIY = "reative-permeability"

    SCAL_COLORMAP = {
        "Missing": "#ffff00",  # Using yellow if the curve couldn't be found
        "KRW": "#0000aa",
        "KRG": "#ff0000",
        "KROG": "#00aa00",
        "KROW": "#00aa00",
        "PCOW": "#555555",  # Reserving #000000 for reference envelope (scal rec)
        "PCOG": "#555555",
    }

    def __init__(
        self,
        relperm_df: pd.DataFrame,
        webviz_settings: WebvizSettings,
        scal: pd.DataFrame,
        sat_axes_maps: dict,
    ) -> None:
        super().__init__("Relatve permeability")

        self.relperm_df = relperm_df
        self.plotly_theme = webviz_settings.theme.plotly_theme
        self.scal = scal
        self.sat_axes_maps = sat_axes_maps

        # Creating the column and row for the setup of the view
        column = self.add_column()
        first_row = column.make_row()
        first_row.add_view_element(Graph(), RelpermCappres.IDs.RELATIVE_PERMEABILIY)

    @property
    def sat_axes(self) -> List[str]:
        """List of all possible saturation axes in dataframe"""
        return [sat for sat in self.sat_axes_maps if sat in self.relperm_df.columns]

    @property
    def ensembles(self) -> List[str]:
        """List of all possible ensembles in dataframe"""
        return list(self.relperm_df["ENSEMBLE"].unique())

    @property
    def satnums(self) -> List[int]:
        """List of all possible satnums in dataframe"""
        return list(self.relperm_df["SATNUM"].unique())

    @property
    def color_options(self) -> List[str]:
        """Options to color by"""
        return ["ENSEMBLE", "CURVE", "SATNUM"]

    @property
    def ens_colors(self) -> dict:
        """Colors for graphs filteres by ensemble"""
        return {
            ens: self.plotly_theme["layout"]["colorway"][self.ensembles.index(ens)]
            for ens in self.ensembles
        }

    @property
    def satnum_colors(self) -> dict:
        """Colors for graphs filtered by satnum"""
        return {
            satnum: (
                self.plotly_theme["layout"]["colorway"][
                    self.satnums.index(satnum)
                    % len(self.plotly_theme["layout"]["colorway"])
                ]
            )
            for satnum in self.satnums
        }

    def set_callbacks(self) -> None:
        """Defines the callback for changing the graphs"""
        # pylint: disable=too-many-statements

        @callback(
            Output(
                self.view_element(RelpermCappres.IDs.RELATIVE_PERMEABILIY)
                .component_unique_id(Graph.IDs.GRAPH)
                .to_string(),
                "figure",
            ),
            Input(
                self.get_store_unique_id(PlugInIDs.Stores.Selectors.SATURATION_AXIS),
                "data",
            ),
            Input(
                self.get_store_unique_id(PlugInIDs.Stores.Selectors.COLOR_BY), "data"
            ),
            Input(
                self.get_store_unique_id(PlugInIDs.Stores.Selectors.ENSAMBLES), "data"
            ),
            Input(self.get_store_unique_id(PlugInIDs.Stores.Selectors.CURVES), "data"),
            Input(self.get_store_unique_id(PlugInIDs.Stores.Selectors.SATNUM), "data"),
            Input(
                self.get_store_unique_id(PlugInIDs.Stores.Visualization.LINE_TRACES),
                "data",
            ),
            Input(
                self.get_store_unique_id(PlugInIDs.Stores.Visualization.Y_AXIS), "data"
            ),
            Input(
                self.get_store_unique_id(PlugInIDs.Stores.SCALRecomendation.SHOW_SCAL),
                "data",
            ),
        )
        def _update_graph(
            sataxis: str,
            color_by: str,
            ensembles: List[str],
            curves: List[str],
            satnums: List[int],
            line_traces: List[str],
            y_axis: str,
            scal: str,
        ) -> dict:
            """Updating graphs according to chosen settings"""

            if not curves or not satnums:  # Curve and satnum has to be defined
                raise PreventUpdate
            if ensembles is None:  # Allowing no ensembles to plot only SCAL data
                ensembles = []

            # Ensuring correct types for the variables
            if not isinstance(ensembles, list):
                ensembles = [ensembles]
            if not isinstance(curves, list):
                curves = [curves]
            if not isinstance(satnums, list):
                satnums = [satnums]
            if not isinstance(sataxis, str):
                sataxis = sataxis[0]
            if not isinstance(color_by, str):
                color_by = color_by[0]

            # Filtering dataframe
            df = filter_df(self.relperm_df, ensembles, curves, satnums, sataxis)

            if color_by == "ENSEMBLE":
                colors = self.ens_colors
            elif color_by == "SATNUM":
                colors = self.satnum_colors
            else:
                colors = RelpermCappres.SCAL_COLORMAP

            nplots = (
                2
                if any(curve.startswith("PC") for curve in curves)
                and any(curve.startswith("KR") for curve in curves)
                else 1
            )

            # Creating the layout of graphs
            layout = plot_layout(
                nplots, curves, sataxis, color_by, y_axis, self.plotly_theme["layout"]
            )

            # Creating the graphs
            if line_traces.lower() == "individual-realizations" and not df.empty:
                data = realization_traces(
                    df,
                    sataxis,
                    color_by,
                    curves,
                    colors,
                    nplots,
                )
            elif line_traces.lower() == "statistical-fanchart" and not df.empty:
                data = statistic_traces(
                    df,
                    sataxis,
                    color_by,
                    curves,
                    colors,
                    nplots,
                )
            else:
                data = []

            if self.scal is not None and "show_scal" in scal:
                scal_df = filter_scal_df(self.scal, curves, satnums, sataxis)
                data.extend(add_scal_traces(scal_df, curves, sataxis, nplots))

            return {"data": data, "layout": layout}

        def filter_df(
            df: pd.DataFrame,
            ensembles: List[str],
            curves: List[str],
            satnums: List[int],
            sataxis: str,
        ) -> pd.DataFrame:
            """Filters dataframe according to chosen settings"""
            df = df.copy()
            df = df.loc[df["ENSEMBLE"].isin(ensembles)]
            df = df.loc[df["SATNUM"].isin(satnums)]
            columns = ["ENSEMBLE", "REAL", "SATNUM"] + [sataxis] + curves
            return df[columns].dropna(axis="columns", how="all")

        def realization_traces(
            df: pd.DataFrame,
            sataxis: str,
            color_by: List[str],
            curves: List[str],
            colors: dict,
            nplots: int,
        ) -> List:
            """Creating graphs in the case of statistcal traces"""

            data = []
            for curve_no, curve in enumerate(curves):
                yaxis = "y" if nplots == 1 or curve.startswith("KR") else "y2"
                xaxis = "x" if yaxis == "y" else "x2"
                if color_by == "CURVE":
                    satnum = df["SATNUM"].iloc[0]
                    ensemble = df["ENSEMBLE"].iloc[0]

                    data.extend(
                        [
                            {
                                "type": "scatter",
                                "x": real_df[sataxis],
                                "y": real_df[curve],
                                "xaxis": xaxis,
                                "yaxis": yaxis,
                                "hovertext": (
                                    f"{curve}, Satnum: {satnum}<br>"
                                    f"Realization: {real}, Ensemble: {ensemble}"
                                ),
                                "name": curve,
                                "legendgroup": curve,
                                "marker": {
                                    "color": colors.get(
                                        curve, colors[list(colors.keys())[0]]
                                    )
                                },
                                "showlegend": real_no == 0,
                            }
                            for real_no, (real, real_df) in enumerate(
                                df.groupby("REAL")
                            )
                        ]
                    )
                else:
                    const_group = (
                        df["SATNUM"].iloc[0]
                        if color_by == "ENSEMBLE"
                        else df["ENSEMBLE"].iloc[0]
                    )
                    data.extend(
                        [
                            {
                                "type": "scatter",
                                "x": real_df[sataxis],
                                "y": real_df[curve],
                                "xaxis": xaxis,
                                "yaxis": yaxis,
                                "hovertext": (
                                    f"{curve}, Satnum: "
                                    f"{group if color_by.upper() == 'SATNUM' else const_group}<br>"
                                    f"Realization: {real}, Ensemble: "
                                    f"{group if color_by.upper() == 'ENSEMBLE' else const_group}"
                                ),
                                "name": group,
                                "legendgroup": group,
                                "marker": {
                                    "color": colors.get(
                                        group, colors[list(colors.keys())[-1]]
                                    )
                                },
                                "showlegend": real_no == 0 and curve_no == 0,
                            }
                            for (group, grouped_df) in df.groupby(color_by)
                            for real_no, (real, real_df) in enumerate(
                                grouped_df.groupby("REAL")
                            )
                        ]
                    )
            return data

        def statistic_traces(
            df: pd.DataFrame,
            sataxis: str,
            color_by: List[str],
            curves: List[str],
            colors: dict,
            nplots: int,
        ) -> List:
            # pylint: disable=too-many-locals
            """Creating graphs in the case of statistcal traces"""
            # Switched P10 and P90 due to convetion in petroleum industry
            def p10(x):
                return np.nanpercentile(x, q=90)

            def p90(x):
                return np.nanpercentile(x, q=10)

            data = []
            for ensemble_no, (ensemble, ensemble_df) in enumerate(
                df[["ENSEMBLE", "SATNUM"] + [sataxis] + curves].groupby(["ENSEMBLE"])
            ):
                for satnum_no, (satnum, satnum_df) in enumerate(
                    ensemble_df.groupby("SATNUM")
                ):
                    df_stat = (
                        satnum_df.groupby(sataxis)
                        .agg([np.nanmean, np.nanmin, np.nanmax, p10, p90])
                        .stack()
                        .swaplevel()
                    )
                    for curve_no, curve in enumerate(curves):
                        yaxis = "y" if nplots == 1 or curve.startswith("KR") else "y2"
                        xaxis = "x" if yaxis == "y" else "x2"
                        legend_group = (
                            curve
                            if color_by.upper() == "CURVE"
                            else ensemble
                            if color_by.upper() == "ENSEMBLE"
                            else satnum
                        )
                        show_legend = (
                            bool(
                                color_by == "CURVE"
                                and ensemble_no == 0
                                and satnum_no == 0
                            )
                            or bool(
                                color_by == "ENSEMBLE"
                                and curve_no == 0
                                and satnum_no == 0
                            )
                            or bool(
                                color_by == "SATNUM"
                                and curve_no == 0
                                and ensemble_no == 0
                            )
                        )

                        data.extend(
                            _get_fanchart_traces(
                                df_stat[curve],
                                colors.get(
                                    legend_group, colors[list(colors.keys())[0]]
                                ),
                                xaxis,
                                yaxis,
                                legend_group,
                                show_legend,
                                curve,
                                ensemble,
                                satnum,
                            )
                        )

            return data

        def _get_fanchart_traces(
            curve_stats: pd.DataFrame,
            color: str,
            xaxis: str,
            yaxis: str,
            legend_group: str,
            show_legend: bool,
            curve: str,
            ensemble: str,
            satnum: int,
        ) -> List:
            # pylint: disable=too-many-arguments
            """Renders a fanchart"""

            # Retrieve indices from one of the keys in series
            x = curve_stats["nanmax"].index.tolist()
            data = FanchartData(
                samples=x,
                low_high=LowHighData(
                    low_data=curve_stats["p90"].values,
                    low_name="P90",
                    high_data=curve_stats["p10"].values,
                    high_name="P10",
                ),
                minimum_maximum=MinMaxData(
                    minimum=curve_stats["nanmin"].values,
                    maximum=curve_stats["nanmax"].values,
                ),
                free_line=FreeLineData("Mean", curve_stats["nanmean"].values),
            )

            hovertemplate = f"{curve} <br>" f"Ensemble: {ensemble}, Satnum: {satnum}"

            return get_fanchart_traces(
                data=data,
                hex_color=color,
                legend_group=legend_group,
                xaxis=xaxis,
                yaxis=yaxis,
                hovertext=hovertemplate,
                show_legend=show_legend,
            )

        def plot_layout(
            nplots: int,
            curves: List[str],
            sataxis: str,
            color_by: List[str],
            y_axis: str,
            theme: dict,
        ) -> dict:
            """Creating the layout around the graphs"""
            titles = (
                ["Relative Permeability", "Capillary Pressure"]
                if nplots == 2
                else ["Relative Permeability"]
                if any(curve.startswith("KR") for curve in curves)
                else ["Capillary Pressure"]
            )

            layout = {}
            layout.update(theme)
            layout.update(
                {
                    "hovermode": "closest",
                    "uirevision": f"sa:{sataxis}_{y_axis}_curves:{'_'.join(sorted(curves))}",
                }
            )

            # Create subplots
            layout.update(
                {
                    "annotations": [
                        {
                            "showarrow": False,
                            "text": titles[0],
                            "x": 0.5,
                            "xanchor": "center",
                            "xref": "paper",
                            "y": 1.0,
                            "yanchor": "bottom",
                            "yref": "paper",
                            "font": {"size": 16},
                        }
                    ],
                }
                if nplots == 1
                else {
                    "annotations": [
                        {
                            "showarrow": False,
                            "text": titles[0],
                            "x": 0.5,
                            "xanchor": "center",
                            "xref": "paper",
                            "y": 1.0,
                            "yanchor": "bottom",
                            "yref": "paper",
                            "font": {"size": 16},
                        },
                        {
                            "showarrow": False,
                            "text": titles[1],
                            "x": 0.5,
                            "xanchor": "center",
                            "xref": "paper",
                            "y": 0.475,
                            "yanchor": "bottom",
                            "yref": "paper",
                            "font": {"size": 16},
                        },
                    ],
                }
                if nplots == 2
                else {}
            )

            layout["legend"] = {"title": {"text": color_by.lower().capitalize()}}

            # Format axes
            if nplots == 1:
                layout.update(
                    {
                        "xaxis": {
                            "automargin": True,
                            "ticks": "",
                            "zeroline": False,
                            "range": [0, 1],
                            "anchor": "y",
                            "domain": [0.0, 1.0],
                            "title": {
                                "text": sataxis.lower().capitalize(),
                                "standoff": 15,
                            },
                            "showgrid": False,
                            "tickmode": "auto",
                        },
                        "yaxis": {
                            "automargin": True,
                            "ticks": "",
                            "zeroline": False,
                            "anchor": "x",
                            "domain": [0.0, 1.0],
                            "type": y_axis,
                            "showgrid": False,
                        },
                        "margin": {"t": 20, "b": 0},
                    }
                )
                if any(curve.startswith("KR") for curve in curves):
                    layout["yaxis"].update({"title": {"text": "kr"}})
                else:
                    layout["yaxis"].update({"title": {"text": "Pc"}})

            elif nplots == 2:
                layout.update(
                    {
                        "xaxis": {
                            "automargin": True,
                            "zeroline": False,
                            "anchor": "y",
                            "domain": [0.0, 1.0],
                            "matches": "x2",
                            "showticklabels": False,
                            "showgrid": False,
                        },
                        "xaxis2": {
                            "automargin": True,
                            "ticks": "",
                            "showticklabels": True,
                            "zeroline": False,
                            "range": [0, 1],
                            "anchor": "y2",
                            "domain": [0.0, 1.0],
                            "title": {"text": sataxis.lower().capitalize()},
                            "showgrid": False,
                        },
                        "yaxis": {
                            "automargin": True,
                            "ticks": "",
                            "zeroline": False,
                            "anchor": "x",
                            "domain": [0.525, 1.0],
                            "title": {"text": "kr"},
                            "type": y_axis,
                            "showgrid": False,
                        },
                        "yaxis2": {
                            "automargin": True,
                            "ticks": "",
                            "zeroline": False,
                            "anchor": "x2",
                            "domain": [0.0, 0.475],
                            "title": {"text": "Pc"},
                            "type": y_axis,
                            "showgrid": False,
                        },
                        "margin": {"t": 20, "b": 0},
                    }
                )
            return layout

        def filter_scal_df(
            df: pd.DataFrame, curves: List[str], satnums: List[str], sataxis: str
        ) -> pd.DataFrame:
            """Filters dataframe when using SCAL recomendation"""
            df = df.copy()
            df = df.loc[df["SATNUM"].isin(satnums)]
            columns = (
                ["SATNUM", "CASE"]
                + [sataxis]
                + [curve for curve in curves if curve in df.columns]
            )
            return df[columns].dropna()

        def add_scal_traces(
            df: pd.DataFrame, curves: List[str], sataxis: str, nplots: int
        ) -> List:
            """Renders scal recommendation traces"""
            traces = []
            for curve_no, curve in enumerate(
                [curve for curve in curves if curve in df.columns]
            ):
                yaxis = "y" if nplots == 1 or curve.startswith("KR") else "y2"
                xaxis = "x" if yaxis == "y" else "x2"
                traces.extend(
                    [
                        {
                            "type": "scatter",
                            "x": case_df[sataxis],
                            "y": case_df[curve],
                            "xaxis": xaxis,
                            "yaxis": yaxis,
                            "hovertext": (
                                f"{curve}, Satnum: {satnum}<br>"
                                f"{case.lower().capitalize()}"
                            ),
                            "name": "SCAL",
                            "legendgroup": "SCAL",
                            "marker": {
                                "color": "black",
                            },
                            "line": {"dash": "dash"},
                            "showlegend": curve_no == 0
                            and satnum_no == 0
                            and case_no == 0,
                        }
                        for satnum_no, (satnum, satnum_df) in enumerate(
                            df.groupby("SATNUM")
                        )
                        for case_no, (case, case_df) in enumerate(
                            satnum_df.groupby("CASE")
                        )
                    ]
                )
            return traces
