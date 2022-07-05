from fcntl import LOCK_WRITE
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

from ..._plugin_ids import PlugInIDs
from ...view_elements import Graph
from ....._utils.fanchart_plotting import FanchartData, FreeLineData, LowHighData, MinMaxData, get_fanchart_traces

class RelpermCappres(ViewABC):
    '''Add comment descibring the plugin'''
    class IDs:
        '''Different curves to be shown in the view'''
        #pylint: disable=too-few-public-methods
        # en ID pr view element; ett eller to view element?
        # tror jeg går for to view elements
        RELATIVE_PERMEABILIY = "reative-permeability"
        CAPILAR_PRESSURE = "capilar-pressure"

        # don't think I need these
        '''KRW = "KRW"
        KROW = "KROW"
        POW = "POW"

        class Saturations:
            SW = "SW"
            SO = "SO"
            SG = "SG"
            SL = "SL"
        class RelpermFamilies: # the possible keywords in the data files needed in list
            SWOF = "SWOF"
            SGOF = "SGOF"
            SLGOF = "SLGOF"
            SWFN = "SWFN"
            SGFN = "SGFN"
            SOF3 = "SOF3"'''

    # maybe need to add a create csv file in the main class to create one csv file
        
    SATURATIONS = ["SW", "SO", "SG", "SL"]
    RELPERM_FAMILIES = ["SWOF", "SGOF", "SLGOF","SWFN", "SGFN", "SOF3"]
    ENSAMBLES = ["iter-0","iter-3"]
    GRAPHS = ["KRW","KRG","KROG","KROW","PCOW","PCOG"]

    # må ha en utvidet csv fil som har realization og ensamble kolonne
    valid_columns = (["ENSEMBLE", "REAL", "KEYWORD", "SATNUM"] + SATURATIONS + GRAPHS)


    def __init__(self,ensambles: List, relperm_df: pd.DataFrame, scalfile: Path = None,sheet_name: Optional[Union[str, int, list]] = None) -> None:
        # scalfile: Path = None; sets the scal file to be used, if any
        # sheet_name: Optional[Union[str, int, list]] = None which shet to use for the scalfile if it is xlsx formate
        super().__init__("Relatve permeability")

        ''' Data funksjonaliteter

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
        '''
        ''' Data i fil
            Filene er sortert etter realization; 
            each realization has iter-0 and iter-3
            share -> results -> relperm.csv
            velger realization (99 ulike) og iter (2 uliker pr realization) -> totalt 198 filer

            I hver fil er dataen grupert nedover ettter satnum (og keyword?)
            Så er det listet data først for SW og å for SG or alle satnums

            X-aksen til plottene er definer ut ifra SG og SW som går fra 0 til 1
        '''
        
        # extracte the data for the different graphs from the data source relperm_df
        self.relperm_df = relperm_df
        # file with columns: ['ENSEMBLE', 'REAL', 'SW', 'KRW', 'KROW', 'PCOW', 'SATNUM', 'KEYWORD','SG', 'KRG', 'KROG', 'PCOG']
        # all these columns will be in the file input to the class RelpermCappres (change name to end with view to distinguish?)

        # the first setting that ou have to choose is between  gaas and  water, you never have both so can split the dataset in two?
        self.SW_df = self.relperm_df[self.relperm_df["KEYWORD"] == "SWOF"]
        self.SW_df = self.relperm_df[self.relperm_df["KEYWORD"] == "SGOF"]

        # creating the columns and row to define the setup of the view
        column = self.add_column()

        first_row = column.make_row()
        first_row.add_view_element(Graph(),RelpermCappres.IDs.RELATIVE_PERMEABILIY) 
        # change something in Graph() to be able to get them in the same plot, or add them as on view element?
        # need the height of the Graph() to vary wether we are suppoed to show to graphs or not

    # define the callbacks of the view
    def set_callbacks(self) -> None:
        # callback for the graphs
        @callback( 
            Output(self.view_element(RelpermCappres.IDs.RELATIVE_PERMEABILIY).component_unique_id(Graph.IDs.GRAPH).to_string(),"figure"),

            Input(self.get_store_unique_id(PlugInIDs.Stores.Selectors.SATURATION_AXIS),"data"),
            Input(self.get_store_unique_id(PlugInIDs.Stores.Selectors.COLOR_BY),"data"),
            Input(self.get_store_unique_id(PlugInIDs.Stores.Selectors.ENSAMBLES),"data"),
            Input(self.get_store_unique_id(PlugInIDs.Stores.Selectors.CURVES),"data"),
            Input(self.get_store_unique_id(PlugInIDs.Stores.Selectors.SATNUM),"data"),

            Input(self.get_store_unique_id(PlugInIDs.Stores.Visualization.LINE_TRACES),"data"),
            Input(self.get_store_unique_id(PlugInIDs.Stores.Visualization.Y_AXIS),"data"),

            Input(self.get_store_unique_id(PlugInIDs.Stores.SCALRecomendation.SHOW_SCAL),"data"),
        )
        def _update_graph(sataxis : List[str], color_by : List[str], ensembles : List[str], curves : List[str], satnums : List[str], 
                            line_traces : List[str], y_axis : List[str], scal : List[str]) -> dict:
            ensemble_colors = {"iter-0":"#285d93","iter-3":"#e48c16"}
            curve_colors = {"KRW":"#0000aa","KRG":"#ff0000","KROG":"#00aa00","KROW":"#00aa00","PCOW":"#555555","PCOG":"#555555"}
            satnum_colors = {
                "1": "#285d93",
                "2": "#e48c16",
                "3": "#00aa00",
                "4": "#cc0000",
                "5": "#9f66bb",
                "6": "#b17750",
                "7": "#d59bc5",
                "8": "#555555",
                "9": "#b9c15b",
                "10": "#5bf2e6",
                "11": "#ff0000",
                "12": "#45f03a"
            }
            colors = {"ensemble": ensemble_colors, "curve": curve_colors, "satnum": satnum_colors}

            if not curves or not satnums:  # Curve and satnum has to be defined
                raise PreventUpdate
            if ensembles is None:  # Allowing no ensembles to plot only SCAL data
                ensembles = []
            
            df = self.SG_df if sataxis[0].upper() == "SG" else self.SW_df

            nplots = (
                2
                if any(curve.startswith("PC") for curve in curves)
                and any(curve.startswith("KR") for curve in curves)
                else 1
            )

            layout = plot_layout(nplots,curves,sataxis,color_by,y_axis)

            if line_traces[0].lower() == "individual realization" and not df.empty:
                data = realization_traces(df, sataxis, color_by, ensembles, curves, satnums, line_traces, y_axis, scal, colors, nplots)
            elif line_traces[0].lower() == "statistical fanchart" and not df.empty:
                data = statistic_traces(df, sataxis, color_by, ensembles, curves, satnums, line_traces, y_axis, scal, colors, nplots)

            if self.scal is not None and "show_scal" in scal:
                scal_df = filter_scal_df(self.scal, curves, satnums, sataxis[0])
                data.extend(add_scal_traces(scal_df, curves, sataxis[0], nplots))

            return {"data": data, "layout": layout}

        
            
            

        def realization_traces(df: pd.DataFrame, sataxis : List[str], color_by : List[str], ensembles : List[str], 
                            curves : List[str], satnums : List[str], line_traces : List[str], y_axis : List[str], 
                            scal : List[str], colorslist : dict, nplots : int) -> List:
            realizatoins = df["REAL"].unique() # list of all possible realizations
            # traces = [i for i in range(len(realizatoins))]
            colors = colorslist[color_by[0].lower()]

            # my version
            '''
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
            '''

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
                                "x": real_df[sataxis[0]],
                                "y": real_df[curve],
                                "xaxis": xaxis,
                                "yaxis": yaxis,
                                "hovertext": (
                                    f"{curve}, Satnum: {satnum[0]}<br>"
                                    f"Realization: {real}, Ensemble: {ensemble}"
                                ),
                                "name": curve,
                                "legendgroup": curve,
                                "marker": {
                                    "color": colors.get(curve, colors[list(colors.keys())[0]])
                                },
                                "showlegend": real_no == 0,
                            }
                            for real_no, (real, real_df) in enumerate(df.groupby("REAL"))
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
                                "x": real_df[sataxis[0]],
                                "y": real_df[curve],
                                "xaxis": xaxis,
                                "yaxis": yaxis,
                                "hovertext": (
                                    f"{curve}, Satnum: "
                                    f"{group if color_by[0].upper() == 'SATNUM' else constant_group}<br>"
                                    f"Realization: {real}, Ensemble: "
                                    f"{group if color_by[0].upper() == 'ENSEMBLE' else constant_group}"
                                ),
                                "name": group,
                                "legendgroup": group,
                                "marker": {
                                    "color": colors.get(group, colors[list(colors.keys())[-1]])
                                },
                                "showlegend": real_no == 0 and curve_no == 0,
                            }
                            for (group, grouped_df) in df.groupby(color_by[0])
                            for real_no, (real, real_df) in enumerate(
                                grouped_df.groupby("REAL")
                            )
                        ]
                    )
            return data

        def statistic_traces(df : pd.DataFrame, sataxis : List[str], color_by : List[str], ensembles : List[str], curves : List[str], satnums : List[str], 
                            line_traces : List[str], y_axis : List[str], scal : List[str], colorslist: dict, nplots : int) -> List:
            # Switched P10 and P90 due to convetion in petroleum industry
            def p10(x):
                return np.nanpercentile(x, q=90)

            def p90(x):
                return np.nanpercentile(x, q=10)

            data = []           # str       #pd.Dataframe
            for ensemble_no, (ensemble, ensemble_df) in enumerate(
                df[["ENSEMBLE", "SATNUM"] + [sataxis[0]] + curves].groupby(["ENSEMBLE"])
            ):                  # int
                for satnum_no, (satnum, satnum_df) in enumerate(ensemble_df.groupby("SATNUM")):
                    df_stat = (
                        satnum_df.groupby(sataxis[0])
                        .agg([np.nanmean, np.nanmin, np.nanmax, p10, p90])
                        .stack()
                        .swaplevel()
                    )
                    for curve_no, curve in enumerate(curves):
                        yaxis = "y" if nplots == 1 or curve.startswith("KR") else "y2"
                        xaxis = "x" if yaxis == "y" else "x2"
                        legend_group = (
                            curve
                            if color_by[0].upper() == "CURVE"
                            else ensemble
                            if color_by[0].upper() == "ENSEMBLE"
                            else satnum
                        )
                        show_legend = (
                            bool(color_by == "CURVE" and ensemble_no == 0 and satnum_no == 0)
                            or bool(color_by == "ENSEMBLE" and curve_no == 0 and satnum_no == 0)
                            or bool(color_by == "SATNUM" and curve_no == 0 and ensemble_no == 0)
                        )
                        color = (
                            colorslist[color_by[0].lower()][ensemble] 
                            if color_by[0].upper() == "ENSEMBLE"
                            else colorslist[color_by[0].lower()][curve] 
                            if color_by[0].upper() == "ENSEMBLE"
                            else colorslist[color_by[0].lower()][satnum] 
                        )
                        data.extend(
                            _get_fanchart_traces(
                                df_stat[curve],
                                color, # str
                                xaxis,
                                yaxis,
                                legend_group,
                                show_legend,
                                curve, # str
                                ensemble, # str
                                satnum, # int
                            )
                        )
            
            return data

        def _get_fanchart_traces(curve_stats :pd.DataFrame, color : str, xaxis : str, yaxis : str, 
            legend_group: str, show_legend: bool, curve : str, ensemble : str, satnum  : int) -> List :
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

        def plot_layout(nplots : int, curves : List[str], sataxis : List[str], color_by : List[str], y_axis : List[str]):
            """
            Constructing plot layout from scratch as it is more responsive than plotly subplots package.
            """
            titles = (
                ["Relative Permeability", "Capillary Pressure"]
                if nplots == 2
                else ["Relative Permeability"]
                if any(curve.startswith("KR") for curve in curves)
                else ["Capillary Pressure"]
            )
            layout = {
                    "hovermode": "closest",
                    "uirevision": f"sa:{sataxis}_{y_axis[0]}_curves:{'_'.join(sorted(curves))}",
                }
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

            layout["legend"] = {"title": {"text": color_by[0].lower().capitalize()}}
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
                            "title": {"text": sataxis[0].lower().capitalize(), "standoff": 15},
                            "showgrid": False,
                            "tickmode": "auto",
                        },
                        "yaxis": {
                            "automargin": True,
                            "ticks": "",
                            "zeroline": False,
                            "anchor": "x",
                            "domain": [0.0, 1.0],
                            "type": y_axis[0],
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
                            "title": {"text": sataxis[0].lower().capitalize()},
                            "showgrid": False,
                        },
                        "yaxis": {
                            "automargin": True,
                            "ticks": "",
                            "zeroline": False,
                            "anchor": "x",
                            "domain": [0.525, 1.0],
                            "title": {"text": "kr"},
                            "type": y_axis[0],
                            "showgrid": False,
                        },
                        "yaxis2": {
                            "automargin": True,
                            "ticks": "",
                            "zeroline": False,
                            "anchor": "x2",
                            "domain": [0.0, 0.475],
                            "title": {"text": "Pc"},
                            "type": y_axis[0],
                            "showgrid": False,
                        },
                        "margin": {"t": 20, "b": 0},
                    }
                )
            return layout

        def filter_scal_df(df : pd.DataFrame, curves : List[str], satnums : List[str], sataxis : str):
            df = df.copy()
            df = df.loc[df["SATNUM"].isin(satnums)]
            columns = (
                ["SATNUM", "CASE"]
                + [sataxis]
                + [curve for curve in curves if curve in df.columns]
            )
            return df[columns].dropna()

        def add_scal_traces(df : pd.DataFrame, curves : List[str], sataxis : str, nplots : int):
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
                                f"{curve}, Satnum: {satnum}<br>" f"{case.lower().capitalize()}"
                            ),
                            "name": "SCAL",
                            "legendgroup": "SCAL",
                            "marker": {
                                "color": "black",
                            },
                            "line": {"dash": "dash"},
                            "showlegend": curve_no == 0 and satnum_no == 0 and case_no == 0,
                        }
                        for satnum_no, (satnum, satnum_df) in enumerate(df.groupby("SATNUM"))
                        for case_no, (case, case_df) in enumerate(satnum_df.groupby("CASE"))
                    ]
                )
            return traces