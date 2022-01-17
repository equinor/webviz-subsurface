import warnings
from pathlib import Path
from typing import Optional, Union

import numpy as np
import webviz_core_components as wcc
from dash import Input, Output, State, dcc
from dash.exceptions import PreventUpdate
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.common_cache import CACHE
from webviz_config.webviz_assets import WEBVIZ_ASSETS

import webviz_subsurface

from .._datainput.fmu_input import load_csv
from .._datainput.relative_permeability import load_satfunc, load_scal_recommendation
from .._utils.fanchart_plotting import (
    FanchartData,
    FreeLineData,
    LowHighData,
    MinMaxData,
    get_fanchart_traces,
)


class RelativePermeability(WebvizPluginABC):
    """Visualizes relative permeability and capillary pressure curves for FMU ensembles.

---

* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`relpermfile`:** Local path to a csvfile in each realization with dumped relperm data.
* **`scalfile`:** Path to a reference file with SCAL recommendationed data. \
    Path to a single file, **not** per realization/ensemble. The path can be absolute or \
    relative to the `webviz` configuration.
* **`sheet_name`:** Which sheet to use for the `scalfile`, only relevant if `scalfile` is an \
    `xlsx` file (recommended to use csv files with `webviz`).

---
The minimum requirement is to define `ensembles`.

If no `relpermfile` is defined, the relative permeability data will be extracted automatically
from the simulation decks of individual realizations using `fmu-ensemble`and `ecl2df` behind the
scenes. Note that this method can be very slow for larger data decks, and is therefore not
recommended unless you have a very simple model/data deck.

`relpermfile` is a path to a file stored per realization (e.g. in \
`share/results/tables/relperm.csv`). `relpermfile` columns:
* One column named `KEYWORD` or `TYPE`: with Flow/Eclipse style keywords (e.g. `SWOF` and `SGOF`).
* One column named `SATNUM` with integer `SATNUM` regions.
* One column **per** saturation (e.g. `SG` and `SW`).
* One column **per** relative permeability curve (e.g. `KRW`, `KROW` and `KRG`)
* One column **per** capillary pressure curve (e.g. `PCOW`).

The `relpermfile` file can e.g. be dumped to disk per realization by a forward model in ERT that
wraps the command `ecl2csv satfunc input_file -o output_file` (requires that you have `ecl2df`
installed). A typical example could be:
`ecl2csv satfunc eclipse/include/props/relperm.inc -o share/results/tables/relperm.csv`.
[Link to ecl2csv satfunc documentation.](https://equinor.github.io/ecl2df/scripts.html#satfunc)


`scalfile` is a path to __a single file of SCAL recommendations__ (for all
realizations/ensembles). The file has to be compatible with
[pyscal's](https://equinor.github.io/pyscal/pyscal.html#pyscal.\
factory.PyscalFactory.load_relperm_df) input format. Including this file adds reference cases
`Pess`, `Base` and `Opt` to the plots. This file is typically a result of a SCAL study.

`sheet_name` defines the sheet to use in the `scalfile`. Only relevant if `scalfile` is an
`xlsx` file (it is recommended to use `csv` and not `xlsx` for `Webviz`).

* [Example of relpermfile](https://github.com/equinor/webviz-subsurface-testdata/blob/master/\
reek_history_match/realization-0/iter-0/share/results/tables/relperm.csv).
* [Example of scalfile](https://github.com/equinor/\
webviz-subsurface-testdata/blob/master/reek_history_match/share/scal/scalreek.csv).
"""

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
        app,
        webviz_settings: WebvizSettings,
        ensembles: list,
        relpermfile: str = None,
        scalfile: Path = None,
        sheet_name: Optional[Union[str, int, list]] = None,
    ):

        super().__init__()

        WEBVIZ_ASSETS.add(
            Path(webviz_subsurface.__file__).parent
            / "_assets"
            / "css"
            / "block_options.css"
        )

        self.ens_paths = {
            ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
            for ens in ensembles
        }
        self.plotly_theme = webviz_settings.theme.plotly_theme
        self.relpermfile = relpermfile
        if self.relpermfile is not None:
            self.satfunc = load_csv(ensemble_paths=self.ens_paths, csv_file=relpermfile)
            self.satfunc = self.satfunc.rename(str.upper, axis="columns").rename(
                columns={"TYPE": "KEYWORD"}
            )
            if "KEYWORD" not in self.satfunc.columns:
                raise ValueError(
                    "There has to be a KEYWORD or TYPE column with corresponding Eclipse keyword: "
                    "e.g SWOF, SGOF and etc."
                )
            valid_columns = (
                ["ENSEMBLE", "REAL", "KEYWORD", "SATNUM"]
                + RelativePermeability.SATURATIONS
                + [
                    key
                    for key in RelativePermeability.SCAL_COLORMAP
                    if key != "Missing"
                ]
            )
            self.satfunc = self.satfunc[
                [col for col in self.satfunc.columns if col in valid_columns]
            ]
        else:
            self.satfunc = load_satfunc(self.ens_paths)
        if any(
            keyword in RelativePermeability.RELPERM_FAMILIES[1]
            for keyword in self.satfunc["KEYWORD"].unique()
        ):
            self.family = 1
            if any(
                keyword in RelativePermeability.RELPERM_FAMILIES[2]
                for keyword in self.satfunc["KEYWORD"].unique()
            ):
                warnings.warn(
                    (
                        "Mix of keyword family 1 and 2, currently only support one family at the "
                        "time. Dropping all data of family 2 ('SWFN', 'SGFN', 'SGWFN', 'SOF2', "
                        "'SOF3', 'SOF32D') and continues with family 1 ('SWOF', 'SGOF', 'SLGOF')."
                    ),
                )
                self.satfunc = self.satfunc[
                    self.satfunc["KEYWORD"].isin(
                        RelativePermeability.RELPERM_FAMILIES["fam1"]
                    )
                ]
            if "SGOF" in self.satfunc["KEYWORD"].unique():
                if "SLGOF" in self.satfunc["KEYWORD"].unique():
                    warnings.warn(
                        (
                            "Mix of 'SGOF' and 'SLGOF' in ensembles, resulting in non-unique "
                            "horizontal axis ('SG' and 'SL') for 'KRG', 'KROG' and 'PCOG'. "
                            "Dropping all data with 'SLGOF'."
                        ),
                    )
                    self.satfunc = self.satfunc[self.satfunc["KEYWORD"] != "SLGOF"]
                self.sat_axes_maps = {
                    "SW": ["KRW", "KROW", "PCOW"],
                    "SG": ["KRG", "KROG", "PCOG"],
                }
            else:
                self.sat_axes_maps = {
                    "SW": ["KRW", "KROW", "PCOW"],
                    "SL": ["KRG", "KROG", "PCOG"],
                }
        elif not all(
            keyword in RelativePermeability.RELPERM_FAMILIES[2]
            for keyword in self.satfunc["KEYWORD"].unique()
        ):
            raise ValueError(
                "Unrecognized saturation table keyword in data. This should not occur unless "
                "there has been changes to ecl2df. Update of this plugin might be required."
            )
        else:
            self.family = 2
            self.sat_axes_maps = {
                "SW": ["KRW", "PCOW"],
                "SG": ["KRG", "PCOG"],
                "SO": ["KROW", "KROG"],
            }
        self.scalfile = scalfile
        self.sheet_name = sheet_name
        self.scal = (
            load_scal_recommendation(self.scalfile, self.sheet_name)
            if self.scalfile is not None
            else None
        )
        self.set_callbacks(app)

    @property
    def sat_axes(self):
        """List of all possible saturation axes in dataframe"""
        return [sat for sat in self.sat_axes_maps if sat in self.satfunc.columns]

    @property
    def ensembles(self):
        return list(self.satfunc["ENSEMBLE"].unique())

    @property
    def satnums(self):
        return list(self.satfunc["SATNUM"].unique())

    @property
    def color_options(self):
        """Options to color by"""
        return ["ENSEMBLE", "CURVE", "SATNUM"]

    @property
    def ens_colors(self):
        return {
            ens: self.plotly_theme["layout"]["colorway"][self.ensembles.index(ens)]
            for ens in self.ensembles
        }

    @property
    def satnum_colors(self):
        return {
            satnum: self.plotly_theme["layout"]["colorway"][self.satnums.index(satnum)]
            for satnum in self.satnums
        }

    @property
    def tour_steps(self):
        return [
            {
                "id": self.uuid("layout"),
                "content": "Dashboard displaying relative permeability and capillary pressure"
                "data.",
            },
            {
                "id": self.uuid("graph"),
                "content": (
                    "Visualization of curves. "
                    "Different options can be set in the menu to the left."
                    "You can also toggle data on/off by clicking at the legend."
                ),
            },
            {
                "id": self.uuid("sataxis"),
                "content": (
                    "Choose saturation type for your x-axis. Will automatically change available "
                    "options in 'Curves'."
                ),
            },
            {
                "id": self.uuid("color_by"),
                "content": ("Choose basis for your colormap."),
            },
            {
                "id": self.uuid("ensemble"),
                "content": ("Select ensembles."),
            },
            {
                "id": self.uuid("curve_selector"),
                "content": (
                    "Choose curves. Capillary pressures and relative permeabilities will be shown"
                    " in separate plots."
                ),
            },
            {
                "id": self.uuid("satnum"),
                "content": ("Choose SATNUM regions."),
            },
            {
                "id": self.uuid("visualization"),
                "content": (
                    "Choose between different visualizations. 1. Show time series as "
                    "individual lines per realization. 2. Show statistical fanchart per ensemble."
                ),
            },
            {
                "id": self.uuid("linlog"),
                "content": ("Switch between linear and logarithmic y-axis."),
            },
            {
                "id": self.uuid("scal_selector"),
                "content": (
                    "Switch on/off SCAL reference data (requires that the optional scalfile is"
                    " defined)."
                ),
            },
        ]

    @staticmethod
    def set_grid_layout(columns, padding=0):
        return {
            "display": "grid",
            "alignContent": "space-around",
            "justifyContent": "space-between",
            "gridTemplateColumns": f"{columns}",
            "padding": f"{padding}px",
        }

    @property
    def layout(self):
        return wcc.FlexBox(
            id=self.uuid("layout"),
            children=[
                wcc.Frame(
                    id=self.uuid("filters"),
                    style={"flex": "1", "height": "90vh"},
                    children=[
                        wcc.Selectors(
                            label="Selectors",
                            children=[
                                wcc.Dropdown(
                                    label="Saturation axis",
                                    id=self.uuid("sataxis"),
                                    clearable=False,
                                    options=[
                                        {
                                            "label": i.lower().capitalize(),
                                            "value": i,
                                        }
                                        for i in self.sat_axes
                                    ],
                                    value=self.sat_axes[0],
                                ),
                                wcc.Dropdown(
                                    label="Color by",
                                    id=self.uuid("color_by"),
                                    clearable=False,
                                    options=[
                                        {
                                            "label": i.lower().capitalize(),
                                            "value": i,
                                        }
                                        for i in self.color_options
                                    ],
                                    value=self.color_options[0],
                                ),
                                dcc.Store(
                                    id=self.uuid("stored_ensemble"),
                                    storage_type="session",
                                    data={},
                                ),
                                wcc.Dropdown(
                                    label="Ensembles",
                                    id=self.uuid("ensemble"),
                                    clearable=False,
                                    multi=True,
                                    options=[
                                        {"label": i, "value": i} for i in self.ensembles
                                    ],
                                    value=self.ensembles[0],
                                ),
                                wcc.Dropdown(
                                    label="Curves",
                                    id=self.uuid("curve"),
                                    clearable=False,
                                    multi=True,
                                ),
                                dcc.Store(
                                    id=self.uuid("stored_satnum"),
                                    storage_type="session",
                                    data={},
                                ),
                                wcc.Dropdown(
                                    label="Satnum",
                                    id=self.uuid("satnum"),
                                    clearable=False,
                                    multi=True,
                                    options=[
                                        {"label": i, "value": i} for i in self.satnums
                                    ],
                                    value=self.satnums[0],
                                ),
                            ],
                        ),
                        wcc.Selectors(
                            label="Visualization",
                            children=[
                                wcc.RadioItems(
                                    label="Line traces",
                                    id=self.uuid("visualization"),
                                    className="block-options",
                                    options=[
                                        {
                                            "label": "Individual realizations",
                                            "value": "realizations",
                                        },
                                        {
                                            "label": "Statistical fanchart",
                                            "value": "statistics",
                                        },
                                    ],
                                    value="statistics",
                                ),
                                wcc.RadioItems(
                                    label="Y-axis",
                                    id=self.uuid("linlog"),
                                    className="block-options",
                                    options=[
                                        {
                                            "label": "Linear",
                                            "value": "linear",
                                        },
                                        {
                                            "label": "Log",
                                            "value": "log",
                                        },
                                    ],
                                    value="linear",
                                ),
                            ],
                        ),
                        wcc.Selectors(
                            style={"display": "block"}
                            if self.scal is not None
                            else {"display": "none"},
                            id=self.uuid("scal_selector"),
                            label="SCAL recommendation",
                            children=[
                                wcc.Checklist(
                                    id=self.uuid("scal"),
                                    options=[
                                        {
                                            "label": "Show SCAL",
                                            "value": "show_scal",
                                        },
                                    ],
                                    value=["show_scal"]
                                    if self.scal is not None
                                    else [],
                                ),
                            ],
                        ),
                    ],
                ),
                wcc.Frame(
                    color="white",
                    highlight=False,
                    style={"flex": "4", "height": "90vh"},
                    children=wcc.Graph(style={"height": "88vh"}, id=self.uuid("graph")),
                ),
            ],
        )

    def set_callbacks(self, app):
        @app.callback(
            Output(self.uuid("graph"), "figure"),
            [
                Input(self.uuid("color_by"), "value"),
                Input(self.uuid("visualization"), "value"),
                Input(self.uuid("ensemble"), "value"),
                Input(self.uuid("curve"), "value"),
                Input(self.uuid("satnum"), "value"),
                Input(self.uuid("sataxis"), "value"),
                Input(self.uuid("linlog"), "value"),
                Input(self.uuid("scal"), "value"),
            ],
        )
        def _update_graph(
            color_by, visualization, ensembles, curves, satnums, sataxis, linlog, scal
        ):
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
            df = filter_df(self.satfunc, ensembles, curves, satnums, sataxis)
            if color_by == "ENSEMBLE":
                colors = self.ens_colors
            elif color_by == "SATNUM":
                colors = self.satnum_colors
            else:
                colors = RelativePermeability.SCAL_COLORMAP
            nplots = (
                2
                if any(curve.startswith("PC") for curve in curves)
                and any(curve.startswith("KR") for curve in curves)
                else 1
            )
            layout = plot_layout(
                nplots, curves, sataxis, color_by, linlog, self.plotly_theme["layout"]
            )
            if visualization == "realizations" and not df.empty:
                traces = add_realization_traces(
                    df, color_by, curves, sataxis, colors, nplots
                )
            elif visualization == "statistics" and not df.empty:
                traces = add_statistic_traces(
                    df, color_by, curves, sataxis, colors, nplots
                )
            else:
                traces = []

            if self.scal is not None and "show_scal" in scal:
                scal_df = filter_scal_df(self.scal, curves, satnums, sataxis)
                traces.extend(add_scal_traces(scal_df, curves, sataxis, nplots))
            return {"data": traces, "layout": layout}

        @app.callback(
            [
                Output(self.uuid("ensemble"), "multi"),
                Output(self.uuid("ensemble"), "value"),
            ],
            [Input(self.uuid("color_by"), "value")],
            [State(self.uuid("stored_ensemble"), "data")],
        )
        def _set_ensemble_selector(color_by, stored_ensemble):
            """If ensemble is selected as color by, set the ensemble
            selector to allow multiple selections, else use stored_ensemble
            """

            if color_by == "ENSEMBLE":
                return True, self.ensembles

            return (
                False,
                stored_ensemble.get("ENSEMBLE", self.ensembles[0]),
            )

        @app.callback(
            [
                Output(self.uuid("satnum"), "multi"),
                Output(self.uuid("satnum"), "value"),
            ],
            [Input(self.uuid("color_by"), "value")],
            [State(self.uuid("stored_satnum"), "data")],
        )
        def _set_satnum_selector(color_by, stored_satnum):
            """If satnum is selected as color by, set the satnum
            selector to allow multiple selections, else use stored_satnum
            """

            if color_by == "SATNUM":
                return True, self.satnums

            return (
                False,
                stored_satnum.get("SATNUM", self.satnums[0]),
            )

        @app.callback(
            [
                Output(self.uuid("curve"), "value"),
                Output(self.uuid("curve"), "options"),
            ],
            [Input(self.uuid("sataxis"), "value")],
        )
        def _set_curve_selector(sataxis):
            """If satnum is selected as color by, set the satnum
            selector to allow multiple selections, else use stored_satnum
            """
            return (
                self.sat_axes_maps[sataxis],
                [
                    {
                        "label": i,
                        "value": i,
                    }
                    for i in self.sat_axes_maps[sataxis]
                ],
            )

    def add_webvizstore(self):
        return [
            (
                load_satfunc,
                [
                    {
                        "ensemble_paths": self.ens_paths,
                        "ensemble_set_name": "EnsembleSet",
                    }
                ],
            )
            if self.relpermfile is None
            else (
                load_csv,
                [
                    {
                        "ensemble_paths": self.ens_paths,
                        "csv_file": self.relpermfile,
                        "ensemble_set_name": "EnsembleSet",
                    }
                ],
            )
        ] + (
            []
            if self.scalfile is None
            else [
                (
                    load_scal_recommendation,
                    [{"scalfile": self.scalfile, "sheet_name": self.sheet_name}],
                )
            ]
        )


# Caching should be safe here with DataFrame as it is always the same for an instance of the plugin.
@CACHE.memoize(timeout=CACHE.TIMEOUT)
def filter_df(df, ensembles, curves, satnums, sataxis):
    df = df.copy()
    df = df.loc[df["ENSEMBLE"].isin(ensembles)]
    df = df.loc[df["SATNUM"].isin(satnums)]
    columns = ["ENSEMBLE", "REAL", "SATNUM"] + [sataxis] + curves
    return df[columns].dropna()


# Caching should be safe here with DataFrame as it is always the same for an instance of the plugin.
@CACHE.memoize(timeout=CACHE.TIMEOUT)
def filter_scal_df(df, curves, satnums, sataxis):
    df = df.copy()
    df = df.loc[df["SATNUM"].isin(satnums)]
    columns = (
        ["SATNUM", "CASE"]
        + [sataxis]
        + [curve for curve in curves if curve in df.columns]
    )
    return df[columns].dropna()


def add_realization_traces(df, color_by, curves, sataxis, colors, nplots):
    """Renders line traces for individual realizations"""
    traces = []

    for curve_no, curve in enumerate(curves):
        yaxis = "y" if nplots == 1 or curve.startswith("KR") else "y2"
        xaxis = "x" if yaxis == "y" else "x2"
        if color_by == "CURVE":
            satnum = df["SATNUM"].iloc[0]
            ensemble = df["ENSEMBLE"].iloc[0]

            traces.extend(
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
            traces.extend(
                [
                    {
                        "type": "scatter",
                        "x": real_df[sataxis],
                        "y": real_df[curve],
                        "xaxis": xaxis,
                        "yaxis": yaxis,
                        "hovertext": (
                            f"{curve}, Satnum: "
                            f"{group if color_by == 'SATNUM' else constant_group}<br>"
                            f"Realization: {real}, Ensemble: "
                            f"{group if color_by == 'ENSEMBLE' else constant_group}"
                        ),
                        "name": group,
                        "legendgroup": group,
                        "marker": {
                            "color": colors.get(group, colors[list(colors.keys())[-1]])
                        },
                        "showlegend": real_no == 0 and curve_no == 0,
                    }
                    for (group, grouped_df) in df.groupby(color_by)
                    for real_no, (real, real_df) in enumerate(
                        grouped_df.groupby("REAL")
                    )
                ]
            )
    return traces


def add_scal_traces(df, curves, sataxis, nplots):
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


# pylint: disable=too-many-locals
def add_statistic_traces(df, color_by, curves, sataxis, colors, nplots):
    """Calculate statistics and call fanchart rendering"""
    # Switched P10 and P90 due to convetion in petroleum industry
    def p10(x):
        return np.nanpercentile(x, q=90)

    def p90(x):
        return np.nanpercentile(x, q=10)

    traces = []
    for ens_no, (ens, ens_df) in enumerate(
        df[["ENSEMBLE", "SATNUM"] + [sataxis] + curves].groupby(["ENSEMBLE"])
    ):
        for satnum_no, (satnum, satnum_df) in enumerate(ens_df.groupby("SATNUM")):
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
                    if color_by == "CURVE"
                    else ens
                    if color_by == "ENSEMBLE"
                    else satnum
                )
                show_legend = (
                    bool(color_by == "CURVE" and ens_no == 0 and satnum_no == 0)
                    or bool(color_by == "ENSEMBLE" and curve_no == 0 and satnum_no == 0)
                    or bool(color_by == "SATNUM" and curve_no == 0 and ens_no == 0)
                )
                traces.extend(
                    _get_fanchart_traces(
                        df_stat[curve],
                        colors.get(legend_group, colors[list(colors.keys())[0]]),
                        xaxis,
                        yaxis,
                        legend_group,
                        show_legend,
                        curve,
                        ens,
                        satnum,
                    )
                )
    return traces


# pylint: disable=too-many-arguments
def _get_fanchart_traces(
    curve_stats,
    color,
    xaxis,
    yaxis,
    legend_group: str,
    show_legend: bool,
    curve,
    ens,
    satnum,
):
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

    hovertemplate = f"{curve} <br>" f"Ensemble: {ens}, Satnum: {satnum}"

    return get_fanchart_traces(
        data=data,
        hex_color=color,
        legend_group=legend_group,
        xaxis=xaxis,
        yaxis=yaxis,
        hovertext=hovertemplate,
        show_legend=show_legend,
    )


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def plot_layout(nplots, curves, sataxis, color_by, linlog, theme):
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
    layout = {}
    layout.update(theme)
    layout.update(
        {
            "hovermode": "closest",
            "uirevision": f"sa:{sataxis}_{linlog}_curves:{'_'.join(sorted(curves))}",
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
                    "title": {"text": sataxis.lower().capitalize(), "standoff": 15},
                    "showgrid": False,
                    "tickmode": "auto",
                },
                "yaxis": {
                    "automargin": True,
                    "ticks": "",
                    "zeroline": False,
                    "anchor": "x",
                    "domain": [0.0, 1.0],
                    "type": linlog,
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
                    "type": linlog,
                    "showgrid": False,
                },
                "yaxis2": {
                    "automargin": True,
                    "ticks": "",
                    "zeroline": False,
                    "anchor": "x2",
                    "domain": [0.0, 0.475],
                    "title": {"text": "Pc"},
                    "type": linlog,
                    "showgrid": False,
                },
                "margin": {"t": 20, "b": 0},
            }
        )
    return layout
