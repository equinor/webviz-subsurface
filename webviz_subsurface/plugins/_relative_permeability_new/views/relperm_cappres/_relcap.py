from fcntl import LOCK_WRITE
from logging import Filter
from pydoc import doc
from typing import List, Tuple, Optional, Union
from pathlib import Path

from dash import callback, Input, Output, State
from matplotlib.pyplot import figure
import pandas as pd
import numpy as np
import plotly.colors
from dash.exceptions import PreventUpdate
from webviz_config.webviz_plugin_subclasses import ViewABC
from webviz_config import WebvizPluginABC, WebvizSettings

from ..._plugin_ids import PlugInIDs
from ...view_elements import Graph
from ....._utils.fanchart_plotting import (
    FanchartData,
    FreeLineData,
    LowHighData,
    MinMaxData,
    get_fanchart_traces,
)
from ...shared_settings._filter import (
    Filter,
    Selectors,
    Scal_recommendation,
    Visualization,
)


class RelpermCappres(ViewABC):
    """Add comment descibring the plugin"""

    class IDs:
        # pylint: disable=too-few-public-methods
        RELATIVE_PERMEABILIY = "reative-permeability"

    # må sjekke om jeg egt trenger disse
    SATURATIONS = ["SW", "SO", "SG", "SL"]
    RELPERM_FAMILIES = {
        1: ["SWOF", "SGOF", "SLGOF"],
        2: ["SWFN", "SGFN", "SOF3"],
    }
    SCAL_COLORMAP = {
        "Missing": "#ffff00",  # using yellow if the curve could not be found
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
    ) -> None:
        super().__init__("Relatve permeability")

        """ Data funksjonaliteter

            Dataen er fordelt mellom de som er saturated in w og g (guess water and gass)
            -> Sat ax Sw: kan velge mellom KRW, KROW og POW (tre grupper)
            -> Sat ax Sg: kan velge mellom KRG, KROG og POG
            Alle disse har felles instilliner

            Gruppene er 
            -> KRW: Relative permeability to water
            -> KRG: Rlative permeability to gas 
            -> KROW: Relative permeability of oil in prescence of water
            -> KROG: Relative permeability of oil in prescence of gas afo liwuid saturation
            -> POW/G: Pressure of Water/Gas

            Colr by: velger hvordan man skal fordele dataen innad i de tre gruppene -> ensamble, curve og satnum
            -> Ensamble: velger hvilke og hvor mange iter du skal ha med og velger en satnum. plotter for hver iter
            -> Curve: velger en iter og en satnum, plotter for hver gruppe/kurve
            -> Satnum: velger en iter og en eler flere satnum, plotte for hver satnum
            Men alle har alltid mulighet til velge hvilke(n) gruppe(r) man ønsker å inludere

            De tre ulike gruppene er hver sin graph i viewen; 
            KRx og KROx er plottet sammen mot samme y akse, alle har samme y akse
            -> KROx: oppe fra venstre og ned til høyre
            -> KRx: nede fra venstre og opp til høyre
            -> POx: 
        """
        """ Data i fil
            Filene er sortert etter realization; 
            each realization has iter-0 and iter-3
            share -> results -> relperm.csv
            velger realization (99 ulike) og iter (2 uliker pr realization) -> totalt 198 filer

            I hver fil er dataen grupert nedover ettter satnum (og keyword?)
            Så er det listet data først for SW og å for SG or alle satnums

            X-aksen til plottene er definer ut ifra SG og SW som går fra 0 til 1
        """

        self.relperm_df = relperm_df
        # file with columns: ['ENSEMBLE', 'REAL', 'SW', 'KRW', 'KROW', 'PCOW', 'SATNUM', 'KEYWORD','SG', 'KRG', 'KROG', 'PCOG']

        self.plotly_theme = webviz_settings.theme.plotly_theme

        self.scal = scal

        # creating the columns and row to define the setup of the view
        column = self.add_column()

        first_row = column.make_row()
        first_row.add_view_element(Graph(), RelpermCappres.IDs.RELATIVE_PERMEABILIY)

    # nå er disse her og i filter, burde kanskje flyttes til plugin.py? også ha de felles?
    @property
    def sat_axes(self) -> List[str]:
        """List of all saturation axes in the dataframe"""
        return [sat for sat in self.sat_axes_maps if sat in self.relperm_df.columns]

    @property
    def ensembles(self):
        """List of all ensembles in the dataframe"""
        return list(self.relperm_df["ENSEMBLE"].unique())

    @property
    def satnums(self):
        """List of all satnums in the dataframe"""
        return list(self.relperm_df["SATNUM"].unique())

    @property
    def color_options(self) -> List[str]:
        """Options to color by"""
        return ["ENSEMBLE", "CURVE", "SATNUM"]

    @property
    def ens_colors(self) -> dict:
        return {
            ens: self.plotly_theme["layout"]["colorway"][self.ensembles.index(ens)]
            for ens in self.ensembles
        }

    @property
    def satnum_colors(self):
        return {
            satnum: (
                self.plotly_theme["layout"]["colorway"][self.satnums.index(satnum) % 10]
                # if self.satnums.index(satnum) < 10
                # else self.plotly_theme["layout"]["colorway"][
                #    self.satnums.index(satnum) - 10
                # ]
            )
            # self.plotly_theme har bare 10 farger, trenger minst to til...?
            for satnum in self.satnums
        }

    def set_callbacks(self) -> None:
        """Defines the callback for the view element"""

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
            color_by: List[str],
            ensembles: List[str],
            curves: List[str],
            satnums: List[int],
            line_traces: List[str],
            y_axis: str,
            scal: List[str],  # kanskje ikke list?
        ) -> dict:

            # sataxis = "SG"
            # color_by = "SATNUM"
            # ensembles = ["iter-0"]
            # curves = ["KRG", "KROG", "PCOG"]
            # satnums = [1, 2, 3, 4, 5]
            # line_traces = "individual-realizations"
            # y_axis = "linear"

            if not curves or not satnums:  # Curve and satnum has to be defined
                raise PreventUpdate
            if ensembles is None:  # Allowing no ensembles to plot only SCAL data
                ensembles = []
            if not isinstance(ensembles, list):
                ensembles = [ensembles]
            if not isinstance(curves, list):
                curves = [curves]
            if not isinstance(satnums, list):
                satnums = [satnums]
            if not isinstance(sataxis, str):
                sataxis = sataxis[0]

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

            layout = plot_layout(
                nplots, curves, sataxis, color_by, y_axis, self.plotly_theme["layout"]
            )

            if line_traces.lower() == "individual-realizations" and not df.empty:
                data = realization_traces(
                    df,
                    sataxis,
                    color_by,
                    ensembles,
                    curves,
                    satnums,
                    line_traces,
                    y_axis,
                    scal,
                    colors,
                    nplots,
                )
            elif line_traces.lower() == "statistical-fanchart" and not df.empty:
                data = statistic_traces(
                    df,
                    sataxis,
                    color_by,
                    ensembles,
                    curves,
                    satnums,
                    line_traces,
                    y_axis,
                    scal,
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
            # det er feil i filter.py hvor options er feil liste
            satnums: List[int],
            sataxis: str,
        ):
            df = df.copy()
            df = df.loc[df["ENSEMBLE"].isin(ensembles)]
            df = df.loc[df["SATNUM"].isin(satnums)]
            columns = ["ENSEMBLE", "REAL", "SATNUM"] + [sataxis] + curves
            # nå e sataxis en liste med et element eller av og til er det en str?? hmm..
            return df[columns].dropna(axis="columns", how="all")

        def realization_traces(
            df: pd.DataFrame,
            sataxis: str,
            color_by: List[str],
            ensembles: List[str],
            curves: List[str],
            satnums: List[str],
            line_traces: List[str],
            y_axis: List[str],
            scal: List[str],
            colors,
            nplots: int,
        ) -> List:
            # my version
            """
            if color_by[0].lower() == "ensemble":
                data = [
                    {
                        "x" : list(df.loc[df["REAL" == realization]].loc[df["ENSEMBLE" == iter]].loc[df["SATNUM"] == satnums[0]]
                        .dropna(axis = "columns", how = "all")[curves[curve]].values.tolist()),
                        "y" : list(df.loc[df["REAL" == realization]].loc[df["ENSEMBLE" == iter]]
                        .loc[df["SATNUM"] == satnums[0]].dropna(axis = "columns", how = "all")[sataxis[0]].values.tolist()), # must include for linear or loganithmic
                        "type" : "line",
                        "legendgroup": iter,
                        "color" : colors[iter],
                        "showlegend": realization_iter == 0 and curvenum == 0,
                    }
                    for realization_iter,realization in enumerate(realizatoins)
                    for iter in ensembles
                    for curvenum,curve in enumerate(curves)
                ]
                layout = plot_layout(nplots,curves,sataxis,color_by,y_axis),
            elif color_by[0].lower() == "curve":
                data = [
                    { # trenger man tolist() og list? og må man ha med [0]
                        "x" : list(df.loc[df["REAL" == realization]].loc[df["ENSEMBLE" == ensembles[0]]].loc[df["SATNUM"] == satnums[0]]
                        [curves[curve]].dropna(axis = "columns", how = "all").values.tolist()),
                        "y" : list(df.loc[df["REAL" == realization]].loc[df["ENSEMBLE" == ensembles[0]]].loc[df["SATNUM"] == satnums[0]]
                        [sataxis[0]].dropna(axis = "columns", how = "all").values.tolist()),
                        "type" : "line",
                        "legendgroup": curve,
                        "color" : colors[curve],
                        "showlegend": realization_iter == 0,
                    }
                    for realization_iter,realization in enumerate(realizatoins)
                    for curve in curves
                ]
            else:
                data = [
                    {
                        "x" : list(df.loc[df["REAL" == realization]].loc[df["ENSEMBLE" == ensembles[0]]].loc[df["SATNUM"] == satnum]
                        [curves[curve]].dropna(axis = "columns", how = "all").values.tolist()),
                        "y" : list(df.loc[df["REAL" == realization]].loc[df["ENSEMBLE" == ensembles[0]]].loc[df["SATNUM"] == satnum]
                        [sataxis[0]].dropna(axis = "columns", how = "all").values.tolist()),
                        "type" : "line",
                        "legendgroup": curve,
                        "color" : colors[satnum],
                        "showlegend": realization_iter == 0 and curvenum == 0,
                    }
                    for satnumiter,satnum in enumerate(satnums)
                    for realization_iter,realization in enumerate(realizatoins)
                    for curvenum,curve in enumerate(curves)
                ]
            """

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
                    constant_group = (
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
                                    f"{group if color_by.upper() == 'SATNUM' else constant_group}<br>"
                                    f"Realization: {real}, Ensemble: "
                                    f"{group if color_by.upper() == 'ENSEMBLE' else constant_group}"
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
            ensembles: List[str],
            curves: List[str],
            satnums: List[str],
            line_traces: List[str],
            y_axis: List[str],
            scal: List[str],
            colors,
            nplots: int,
        ) -> List:
            # Switched P10 and P90 due to convetion in petroleum industry
            def p10(x):
                return np.nanpercentile(x, q=90)

            def p90(x):
                return np.nanpercentile(x, q=10)

            data = (
                []
            )  # dataen her gir fine x-verdier, men bare nan på y-verdiene for alle
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
                                curve,  # str
                                ensemble,  # str
                                satnum,  # int
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
            """Renders a fanchart"""

            # Retrieve indices from one of the keys in series
            x = curve_stats["nanmax"].index.tolist()
            # over tar ut x-verdier som er verdien for SG
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
            theme,
        ):

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
            # create subplots
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
            # format axes
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
                            "type": y_axis,  # her tror jeg ikke [0] er nødvendig
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
        ):
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
        ):
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
