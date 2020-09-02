from pathlib import Path

import numpy as np
import pandas as pd
import dash_html_components as html
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_config import WebvizPluginABC
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore

from webviz_subsurface._utils.unique_theming import unique_colors
from webviz_subsurface._datainput.fmu_input import load_csv
from ._processing import filter_frame
from ._formation_figure import FormationFigure
from ._map_figure import MapFigure
from ._misfit_figure import update_misfit_plot
from ._crossplot_figure import update_crossplot
from ._errorplot_figure import update_errorplot


class RftPlotter(WebvizPluginABC):
    """This plugin visualizes simulated RFT results from
FMU ensembles combined with ERT observation data.

Several visualizations are available:

* Map view of RFT observations.

* Depth vs pressure plot showing simulated RFT data along wells together with observation points.

* Barchart showing sum of mean misfit for ERT observations per realization. One plot per ensemble.

* Crossplot of simulated RFT vs observed value per ERT observation. One plot per ensemble.

* Boxplot showing misfit per ERT observation for each ensemble.

---
**Using data per realization**

* **`ensembles`**: Which ensembles in `shared_settings` to visualize.

In addition, you need to have the following files in your realizations stored at the local path \
`share/results/tables`:

* **`rft.csv`**: A csv file containing simulated RFT data extracted from ECLIPSE RFT output files \
using [ecl2df](https://equinor.github.io/ecl2df/ecl2df.html#module-ecl2df.rft) \
[(example file)](https://github.com/equinor/webviz-subsurface-testdata/blob/master/\
reek_history_match/realization-0/iter-0/share/results/tables/rft.csv).

* **`rft_ert.csv`**: A csv file containing simulated and observed RFT data for RFT observations \
defined in ERT \
[(example file)](https://github.com/equinor/webviz-subsurface-testdata/blob/master/\
reek_history_match/realization-0/iter-0/share/results/tables/rft_ert.csv).


**Using aggregated data**

* **`csvfile_rft`**: Aggregated version of `rft.csv` [(example file)](\
https://github.com/equinor/webviz-subsurface-testdata/blob/master/aggregated_data/rft.csv).
* **`csvfile_rft_ert`**: Aggregated version of `rft_ert.csv` [(example file)](\
https://github.com/equinor/webviz-subsurface-testdata/blob/master/aggregated_data/rft_ert.csv).


**Optional input for both input options**

* **`obsdata`**: A csv file containing additional RFT observation data not defined in ERT for
visualization together with simulated RFT.
Mandatory column names: `WELL`, `DATE` (yyyy-mm-dd), `DEPTH` and `PRESSURE`

* **`formations`**: A csv file containing top and base values for each zone per well.
Used to visualize zone boundaries together with simulated RFT.
Mandatory column names: `WELL`, `ZONE`, `TOP_TVD`, `BASE_TVD` \
[(example file))](\
https://github.com/equinor/webviz-subsurface-testdata/blob/master/\
reek_history_match/share/results/tables/formations.csv).

* **`faultlines`**: A csv file containing faultpolygons to be visualized together with the map view.
Export format from [xtgeo.xyz.polygons.dataframe](
https://xtgeo.readthedocs.io/en/latest/apiref/xtgeo.xyz.polygons.html#xtgeo.xyz.polygons.Polygons.dataframe
) \
[(example file)](\
https://github.com/equinor/webviz-subsurface-testdata/blob/master/\
reek_history_match/share/results/polygons/faultpolygons.csv).

---
?> Well name needs to be consistent with Eclipse well name.

?> Only RFT observations marked as active in ERT are used to generate plots.

?> Only TVD values are supported, plan to support MD values in a later release.

The `rft_ert.csv` file currently lacks a standardized method of generation. A \
**temporary** script can be found [here]\
(https://github.com/equinor/webviz-subsurface-testdata/\
blob/b8b7f1fdd3abc505b137b587dcd9e44bbcf411c9/preprocessing_scripts/ert_rft.py).

"""

    def __init__(
        self,
        app,
        csvfile_rft: Path = None,
        csvfile_rft_ert: Path = None,
        ensembles: list = None,
        formations: Path = None,
        obsdata: Path = None,
        faultlines: Path = None,
    ):
        super().__init__()
        self.formations = formations
        self.faultlines = faultlines
        self.obsdata = obsdata
        self.csvfile_rft = csvfile_rft
        self.csvfile_rft_ert = csvfile_rft_ert
        self.formationdf = read_csv(self.formations) if self.formations else None
        self.faultlinesdf = read_csv(self.faultlines) if self.faultlines else None
        self.obsdatadf = read_csv(self.obsdata) if self.obsdata else None

        if csvfile_rft and ensembles:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile_rft" and "csvfile_rft_ert" or '
                '"ensembles"'
            )

        if csvfile_rft and csvfile_rft_ert:
            self.simdf = read_csv(self.csvfile_rft)
            self.ertdatadf = read_csv(self.csvfile_rft_ert)
        elif ensembles:
            self.ens_paths = (
                {
                    ens: app.webviz_settings["shared_settings"]["scratch_ensembles"][
                        ens
                    ]
                    for ens in ensembles
                }
                if ensembles is not None
                else None
            )

            try:
                self.simdf = load_csv(self.ens_paths, "share/results/tables/rft.csv")
            except KeyError as exc:
                raise KeyError(
                    "Csv file for Eclipse RFT output (share/results/tables/rft.csv) not found!"
                ) from exc

            try:
                self.ertdatadf = load_csv(
                    self.ens_paths, "share/results/tables/rft_ert.csv"
                )
            except KeyError as exc:
                raise KeyError(
                    "Csv file for ERT RFT observations/simulations "
                    "(share/results/tables/rft_ert.csv) not found!"
                ) from exc

        else:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile_rft" and "csvfile_rft_ert" or '
                '"ensembles"'
            )
        self.ertdatadf = self.ertdatadf.rename(
            columns={
                "time": "DATE",
                "isactive": "ACTIVE",
                "well": "WELL",
                "zone": "ZONE",
                "pressure": "SIMULATED",
                "true_vertical_depth": "TVD",
                "obs": "OBS",
                "error": "OBS_ERR",
                "utm_x": "EAST",
                "utm_y": "NORTH",
            }
        )
        self.ertdatadf["DIFF"] = self.ertdatadf["SIMULATED"] - self.ertdatadf["OBS"]
        self.ertdatadf["ABSDIFF"] = abs(
            self.ertdatadf["SIMULATED"] - self.ertdatadf["OBS"]
        )

        self.ertdatadf["YEAR"] = pd.to_datetime(self.ertdatadf["DATE"]).dt.year
        self.ertdatadf["DATE_IDX"] = self.ertdatadf["DATE"].apply(
            lambda x: list(self.ertdatadf["DATE"].unique()).index(x)
        )

        self.ertdatadf = filter_frame(
            self.ertdatadf,
            {
                "ACTIVE": 1,
            },
        )
        self.ertdatadf["STDDEV"] = self.ertdatadf.groupby(
            ["WELL", "DATE", "ZONE", "ENSEMBLE", "TVD"]
        )["SIMULATED"].transform("std")

        self.set_callbacks(app)

    def add_webvizstore(self):

        functions = [
            (
                read_csv,
                [
                    {"csv_file": path}
                    for path in [
                        self.faultlines,
                        self.formations,
                        self.obsdata,
                        self.csvfile_rft,
                        self.csvfile_rft_ert,
                    ]
                    if path is not None
                ],
            )
        ]
        if self.csvfile_rft is None:
            functions.append(
                (
                    load_csv,
                    [
                        {
                            "ensemble_paths": self.ens_paths,
                            "csv_file": "share/results/tables/rft.csv",
                        },
                        {
                            "ensemble_paths": self.ens_paths,
                            "csv_file": "share/results/tables/rft_ert.csv",
                        },
                    ],
                )
            )
        return functions

    @property
    def well_names(self):
        return sorted(list(self.ertdatadf["WELL"].unique()))

    @property
    def zone_names(self):
        return sorted(list(self.ertdatadf["ZONE"].unique()))

    @property
    def dates(self):
        return sorted(list(self.ertdatadf["DATE"].unique()))

    def date_in_well(self, well):
        df = self.ertdatadf.loc[self.ertdatadf["WELL"] == well]

        return [str(d) for d in list(df["DATE"].unique())]

    @property
    def ensembles(self):
        return list(self.ertdatadf["ENSEMBLE"].unique())

    @property
    def enscolors(self):
        return unique_colors(self.ensembles)

    def date_marks(self):

        marks = {}

        idx_steps = np.linspace(
            start=0,
            stop=self.ertdatadf["DATE_IDX"].max(),
            num=min(5, len(self.ertdatadf["DATE_IDX"].unique())),
            dtype=int,
        )

        date_steps = self.ertdatadf.loc[self.ertdatadf["DATE_IDX"].isin(idx_steps)][
            "DATE"
        ].unique()

        for i, date_index in enumerate(idx_steps):
            marks[str(date_index)] = {
                "label": f"{date_steps[i]}",
                "style": {
                    "white-space": "nowrap",
                    "font-weight": "bold",
                },
            }
        return marks

    @property
    def formation_plot_selectors(self):
        return [
            html.Div(
                [
                    html.Label(
                        style={"font-weight": "bold"},
                        children="Ensembles in well plot",
                    ),
                    dcc.Dropdown(
                        id=self.uuid("ensemble"),
                        options=[
                            {"label": ens, "value": ens} for ens in self.ensembles
                        ],
                        value=self.ensembles[0],
                        multi=True,
                        clearable=False,
                    ),
                ]
            ),
            wcc.FlexBox(
                children=[
                    html.Div(
                        style={"flex": 1},
                        children=[
                            html.Label(
                                style={"font-weight": "bold"},
                                children="Well",
                            ),
                            dcc.Dropdown(
                                id=self.uuid("well"),
                                options=[
                                    {"label": well, "value": well}
                                    for well in self.well_names
                                ],
                                value=self.well_names[0],
                                clearable=False,
                            ),
                        ],
                    ),
                    html.Div(
                        style={"flex": 1},
                        children=[
                            html.Label(
                                style={"font-weight": "bold"},
                                children="Date",
                            ),
                            dcc.Dropdown(
                                id=self.uuid("date"),
                                options=[
                                    {"label": date, "value": date}
                                    for date in self.date_in_well(self.well_names[0])
                                ],
                                clearable=False,
                                value=self.date_in_well(self.well_names[0])[0],
                            ),
                        ],
                    ),
                ]
            ),
            html.Div(
                [
                    html.Label(
                        style={"font-weight": "bold"},
                        children="Plot simulated results as",
                    ),
                    dcc.RadioItems(
                        id=self.uuid("linetype"),
                        options=[
                            {
                                "label": "Realization lines",
                                "value": "realization",
                            },
                            {
                                "label": "Statistical fanchart",
                                "value": "fanchart",
                            },
                        ],
                        value="realization",
                        labelStyle={
                            "display": "inline-block",
                            "margin": "5px",
                        },
                    ),
                ]
            ),
        ]

    @property
    def map_plot_selectors(self):

        return (
            html.Div(
                style={"marginRight": "10px"},
                children=[
                    html.Div(
                        style={"width": "50%"},
                        children=[
                            html.Label(
                                style={"font-weight": "bold"},
                                children="Ensemble in map plot",
                            ),
                            dcc.Dropdown(
                                id=self.uuid("map_ensemble"),
                                options=[
                                    {"label": ens, "value": ens}
                                    for ens in list(self.ertdatadf["ENSEMBLE"].unique())
                                ],
                                value=list(self.ertdatadf["ENSEMBLE"].unique())[0],
                                clearable=False,
                            ),
                        ],
                    ),
                    wcc.FlexBox(
                        children=[
                            html.Div(
                                style={"flex": 1},
                                children=[
                                    html.Label(
                                        style={"font-weight": "bold"},
                                        children="Size by",
                                    ),
                                    dcc.Dropdown(
                                        id=self.uuid("map_size"),
                                        options=[
                                            {
                                                "label": "Standard Deviation",
                                                "value": "STDDEV",
                                            },
                                            {
                                                "label": "Misfit",
                                                "value": "ABSDIFF",
                                            },
                                        ],
                                        value="ABSDIFF",
                                        clearable=False,
                                    ),
                                ],
                            ),
                            html.Div(
                                style={"flex": 1},
                                children=[
                                    html.Label(
                                        style={"font-weight": "bold"},
                                        children="Color by",
                                    ),
                                    dcc.Dropdown(
                                        id=self.uuid("map_color"),
                                        options=[
                                            {
                                                "label": "Misfit",
                                                "value": "ABSDIFF",
                                            },
                                            {
                                                "label": "Standard Deviation",
                                                "value": "STDDEV",
                                            },
                                            {
                                                "label": "Year",
                                                "value": "YEAR",
                                            },
                                        ],
                                        value="STDDEV",
                                        clearable=False,
                                    ),
                                ],
                            ),
                        ]
                    ),
                    html.Label(
                        style={"font-weight": "bold"},
                        children="Date range",
                    ),
                    html.Div(
                        style={"width": "100%", "height": "70px"},
                        children=[
                            dcc.RangeSlider(
                                id=self.uuid("map_date"),
                                min=self.ertdatadf["DATE_IDX"].min(),
                                max=self.ertdatadf["DATE_IDX"].max(),
                                value=[
                                    self.ertdatadf["DATE_IDX"].min(),
                                    self.ertdatadf["DATE_IDX"].max(),
                                ],
                                marks=self.date_marks(),
                            )
                        ],
                    ),
                ],
            ),
        )

    def filter_layout(self, tab):
        """Layout for shared filters"""
        return [
            html.Label(
                style={"font-weight": "bold"},
                children=["Ensembles"],
            ),
            wcc.Select(
                size=min(4, len(self.ensembles)),
                id=self.uuid(f"ensemble-{tab}"),
                options=[{"label": name, "value": name} for name in self.ensembles],
                value=self.ensembles,
                multi=True,
            ),
            html.Label(
                style={"font-weight": "bold"},
                children=["Wells"],
            ),
            wcc.Select(
                size=min(20, len(self.well_names)),
                id=self.uuid(f"well-{tab}"),
                options=[{"label": name, "value": name} for name in self.well_names],
                value=self.well_names,
                multi=True,
            ),
            html.Label(
                style={"font-weight": "bold"},
                children=["Zones"],
            ),
            wcc.Select(
                size=min(10, len(self.zone_names)),
                id=self.uuid(f"zone-{tab}"),
                options=[{"label": name, "value": name} for name in self.zone_names],
                value=self.zone_names,
                multi=True,
            ),
            html.Label(
                style={"font-weight": "bold"},
                children=["Dates"],
            ),
            wcc.Select(
                size=min(10, len(self.dates)),
                id=self.uuid(f"date-{tab}"),
                options=[{"label": name, "value": name} for name in self.dates],
                value=self.dates,
                multi=True,
            ),
        ]

    def size_color_layout(self):
        return [
            html.Div(
                children=[
                    html.Label(
                        style={"font-weight": "bold"},
                        children="Color by",
                    ),
                    dcc.Dropdown(
                        id=self.uuid("crossplot_color"),
                        options=[
                            {
                                "label": "Misfit",
                                "value": "ABSDIFF",
                            },
                            {
                                "label": "Standard Deviation",
                                "value": "STDDEV",
                            },
                        ],
                        value="STDDEV",
                        clearable=False,
                    ),
                ],
            ),
            html.Div(
                children=[
                    html.Label(
                        style={"font-weight": "bold"},
                        children="Size by",
                    ),
                    dcc.Dropdown(
                        id=self.uuid("crossplot_size"),
                        options=[
                            {
                                "label": "Standard Deviation",
                                "value": "STDDEV",
                            },
                            {
                                "label": "Misfit",
                                "value": "ABSDIFF",
                            },
                        ],
                        value="ABSDIFF",
                        clearable=False,
                    ),
                ],
            ),
        ]

    @property
    def layout(self):

        tabs_styles = {"height": "44px", "width": "100%"}
        tab_style = {
            "borderBottom": "1px solid #d6d6d6",
            "padding": "6px",
            "fontWeight": "bold",
        }

        tab_selected_style = {
            "borderTop": "1px solid #d6d6d6",
            "borderBottom": "1px solid #d6d6d6",
            "backgroundColor": "#007079",
            "color": "white",
            "padding": "6px",
        }

        return dcc.Tabs(
            style=tabs_styles,
            children=[
                dcc.Tab(
                    label="RFT Map",
                    style=tab_style,
                    selected_style=tab_selected_style,
                    children=[
                        html.Div(
                            children=[
                                wcc.FlexBox(
                                    children=[
                                        html.Div(
                                            style={"flex": 1},
                                            children=self.map_plot_selectors,
                                        ),
                                        html.Div(
                                            style={"flex": 1},
                                            children=self.formation_plot_selectors,
                                        ),
                                    ]
                                ),
                                wcc.FlexBox(
                                    children=[
                                        wcc.Graph(
                                            style={"flex": 1},
                                            id=self.uuid("map"),
                                        ),
                                        wcc.Graph(
                                            style={"flex": 1},
                                            id=self.uuid("graph"),
                                            figure={
                                                "layout": {
                                                    "height": 800,
                                                    "margin": {"t": 50},
                                                    "xaxis": {"showgrid": False},
                                                    "yaxis": {"showgrid": False},
                                                }
                                            },
                                        ),
                                    ]
                                ),
                            ]
                        )
                    ],
                ),
                dcc.Tab(
                    label="RFT misfit per real",
                    style=tab_style,
                    selected_style=tab_selected_style,
                    children=[
                        wcc.FlexBox(
                            children=[
                                html.Div(
                                    style={"flex": 1},
                                    children=self.filter_layout("misfitplot"),
                                ),
                                html.Div(
                                    style={"flex": 4},
                                    id=self.uuid("misfit-graph-wrapper"),
                                ),
                            ]
                        )
                    ],
                ),
                dcc.Tab(
                    label="RFT crossplot - sim vs obs",
                    style=tab_style,
                    selected_style=tab_selected_style,
                    children=[
                        wcc.FlexBox(
                            children=[
                                html.Div(
                                    style={"flex": 1},
                                    children=self.filter_layout("crossplot")
                                    + self.size_color_layout(),
                                ),
                                html.Div(
                                    style={"flex": 4},
                                    children=[
                                        html.Div(
                                            id=self.uuid("crossplot-graph-wrapper")
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
                dcc.Tab(
                    label="RFT misfit per observation",
                    style=tab_style,
                    selected_style=tab_selected_style,
                    children=[
                        wcc.FlexBox(
                            children=[
                                html.Div(
                                    style={"flex": 1},
                                    children=self.filter_layout("errorplot"),
                                ),
                                html.Div(
                                    style={"flex": 4},
                                    children=wcc.Graph(id=self.uuid("errorplot-graph")),
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )

    def set_callbacks(self, app):
        @app.callback(
            Output(self.uuid("well"), "value"),
            [
                Input(self.uuid("map"), "clickData"),
            ],
        )
        def _get_clicked_well(click_data):
            if not click_data:
                return self.well_names[0]
            for layer in click_data["points"]:
                try:
                    return layer["customdata"]
                except KeyError:
                    pass
            raise PreventUpdate

        @app.callback(
            Output(self.uuid("map"), "figure"),
            [
                Input(self.uuid("map_ensemble"), "value"),
                Input(self.uuid("map_size"), "value"),
                Input(self.uuid("map_color"), "value"),
                Input(self.uuid("map_date"), "value"),
            ],
        )
        def _update_map(ensemble, sizeby, colorby, dates):
            figure = MapFigure(self.ertdatadf, ensemble)
            if self.faultlinesdf is not None:
                figure.add_fault_lines(self.faultlinesdf)
            figure.add_misfit_plot(sizeby, colorby, dates)

            return {"data": figure.traces, "layout": figure.layout}

        @app.callback(
            Output(self.uuid("graph"), "figure"),
            [
                Input(self.uuid("well"), "value"),
                Input(self.uuid("date"), "value"),
                Input(self.uuid("ensemble"), "value"),
                Input(self.uuid("linetype"), "value"),
            ],
        )
        def _update_formation_plot(well, date, ensembles, linetype):
            if date not in self.date_in_well(well):
                raise PreventUpdate

            figure = FormationFigure(
                well, self.simdf, self.ertdatadf, self.enscolors, self.obsdatadf
            )
            if self.formations is not None:
                figure.add_formation(self.formationdf)
            if linetype == "realization":
                figure.add_simulated_lines(date, ensembles)
            if linetype == "fanchart":
                figure.add_fanchart(date, ensembles)

            figure.add_observed(date)
            figure.add_ert_observed(date)

            return {
                "data": figure.traces,
                "layout": figure.layout,
            }

        @app.callback(
            [Output(self.uuid("date"), "options"), Output(self.uuid("date"), "value")],
            [
                Input(self.uuid("well"), "value"),
            ],
            [State(self.uuid("date"), "value")],
        )
        def _update_date(well, current_date):
            dates = self.date_in_well(well)
            available_dates = [{"label": date, "value": date} for date in dates]
            date = current_date if current_date in dates else dates[0]
            return available_dates, date

        @app.callback(
            Output(self.uuid("misfit-graph-wrapper"), "children"),
            [
                Input(self.uuid("well-misfitplot"), "value"),
                Input(self.uuid("zone-misfitplot"), "value"),
                Input(self.uuid("date-misfitplot"), "value"),
                Input(self.uuid("ensemble-misfitplot"), "value"),
            ],
        )
        def _misfit_plot(wells, zones, dates, ensembles):
            df = filter_frame(
                self.ertdatadf,
                {"WELL": wells, "ZONE": zones, "DATE": dates, "ENSEMBLE": ensembles},
            )
            return update_misfit_plot(df, self.enscolors)

        @app.callback(
            Output(self.uuid("crossplot-graph-wrapper"), "children"),
            [
                Input(self.uuid("well-crossplot"), "value"),
                Input(self.uuid("zone-crossplot"), "value"),
                Input(self.uuid("date-crossplot"), "value"),
                Input(self.uuid("ensemble-crossplot"), "value"),
                Input(self.uuid("crossplot_size"), "value"),
                Input(self.uuid("crossplot_color"), "value"),
            ],
        )
        def _crossplot(wells, zones, dates, ensembles, sizeby, colorby):
            df = filter_frame(
                self.ertdatadf,
                {"WELL": wells, "ZONE": zones, "DATE": dates, "ENSEMBLE": ensembles},
            )
            return update_crossplot(df, sizeby, colorby)

        @app.callback(
            Output(self.uuid("errorplot-graph"), "figure"),
            [
                Input(self.uuid("well-errorplot"), "value"),
                Input(self.uuid("zone-errorplot"), "value"),
                Input(self.uuid("date-errorplot"), "value"),
                Input(self.uuid("ensemble-errorplot"), "value"),
            ],
        )
        def _errorplot(wells, zones, dates, ensembles):

            df = filter_frame(
                self.ertdatadf,
                {"WELL": wells, "ZONE": zones, "DATE": dates, "ENSEMBLE": ensembles},
            )
            return update_errorplot(df, self.enscolors)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file) -> pd.DataFrame:
    return pd.read_csv(csv_file)
