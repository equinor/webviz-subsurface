from typing import Optional, List, Dict, Tuple, Callable, Any, Union
from pathlib import Path

import dash
import numpy as np
import pandas as pd
import dash_html_components as html
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
import webviz_core_components as wcc
from webviz_config import WebvizPluginABC
from webviz_config import WebvizSettings
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

In addition, you need to have rft-files in your realizations stored at the local path \
`share/results/tables`. The `rft_ert.csv` is required as input, while the `rft.csv` is optional:

* **`rft_ert.csv`**: A csv file containing simulated and observed RFT data for RFT observations \
defined in ERT \
[(example file)](https://github.com/equinor/webviz-subsurface-testdata/blob/master/\
reek_history_match/realization-0/iter-0/share/results/tables/rft_ert.csv).

* **`rft.csv`**: A csv file containing simulated RFT data extracted from ECLIPSE RFT output files \
using [ecl2df](https://equinor.github.io/ecl2df/ecl2df.html#module-ecl2df.rft) \
[(example file)](https://github.com/equinor/webviz-subsurface-testdata/blob/master/\
reek_history_match/realization-0/iter-0/share/results/tables/rft.csv). \
Simulated RFT data can be visualized along MD if a "CONMD" column is present in \
the dataframe and only for wells where each RFT datapoint has a unique MD.

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

The `rft_ert.csv` file can be generated by running the "MERGE_RFT_ERTOBS" forward model in ERT, \
this will collect ERT RFT observations and merge with CSV output from the "GENDATA_RFT" forward \
model. [ERT docs](https://fmu-docs.equinor.com/docs/ert/reference/\
forward_models.html?highlight=gendata_rft#MERGE_RFT_ERTOBS).

"""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        app: dash.Dash,
        webviz_settings: WebvizSettings,
        csvfile_rft: Path = None,
        csvfile_rft_ert: Path = None,
        ensembles: Optional[List[str]] = None,
        formations: Path = None,
        obsdata: Path = None,
        faultlines: Path = None,
    ) -> None:
        super().__init__()
        self.formations = formations
        self.faultlines = faultlines
        self.obsdata = obsdata
        self.csvfile_rft = csvfile_rft
        self.csvfile_rft_ert = csvfile_rft_ert

        self.simdf = read_csv(self.csvfile_rft) if csvfile_rft is not None else None
        self.formationdf = read_csv(self.formations) if self.formations else None
        self.faultlinesdf = read_csv(self.faultlines) if self.faultlines else None
        self.obsdatadf = read_csv(self.obsdata) if self.obsdata else None

        if csvfile_rft_ert and ensembles:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile_rft_ert" or "ensembles"'
            )

        if csvfile_rft_ert is not None:
            self.ertdatadf = read_csv(self.csvfile_rft_ert)

        if ensembles:
            self.ens_paths = (
                {
                    ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
                    for ens in ensembles
                }
                if ensembles is not None
                else None
            )

            try:
                self.simdf = load_csv(self.ens_paths, "share/results/tables/rft.csv")
            except (KeyError, OSError):
                self.simdf = None

            try:
                self.ertdatadf = load_csv(
                    self.ens_paths, "share/results/tables/rft_ert.csv"
                )
            except KeyError as exc:
                raise KeyError(
                    "CSV file for ERT RFT observations/simulations "
                    "(share/results/tables/rft_ert.csv) not found!"
                ) from exc

        self.ertdatadf = self.ertdatadf.rename(
            columns={
                "time": "DATE",
                "is_active": "ACTIVE",
                "isactive": "ACTIVE",
                "well": "WELL",
                "zone": "ZONE",
                "pressure": "SIMULATED",
                "true_vertical_depth": "TVD",
                "measured_depth": "MD",
                "observed": "OBSERVED",
                "obs": "OBSERVED",
                "error": "OBSERVED_ERR",
                "utm_x": "EAST",
                "utm_y": "NORTH",
            }
        )
        self.ertdatadf["DIFF"] = (
            self.ertdatadf["SIMULATED"] - self.ertdatadf["OBSERVED"]
        )
        self.ertdatadf["ABSDIFF"] = abs(
            self.ertdatadf["SIMULATED"] - self.ertdatadf["OBSERVED"]
        )
        self.ertdatadf["YEAR"] = pd.to_datetime(self.ertdatadf["DATE"]).dt.year
        self.ertdatadf = (
            self.ertdatadf.sort_values(  # PyCQA/pylint#4577 # pylint: disable=no-member
                by="DATE"
            )
        )
        self.ertdatadf["DATE_IDX"] = self.ertdatadf["DATE"].apply(
            lambda x: list(self.ertdatadf["DATE"].unique()).index(x)
        )
        self.date_marks = self.set_date_marks()
        self.ertdatadf = filter_frame(
            self.ertdatadf,
            {
                "ACTIVE": 1,
            },
        )
        self.ertdatadf[
            "STDDEV"
        ] = self.ertdatadf.groupby(  # PyCQA/pylint#4577 # pylint: disable=no-member
            ["WELL", "DATE", "ZONE", "ENSEMBLE", "TVD"]
        )[
            "SIMULATED"
        ].transform(
            "std"
        )

        self.set_callbacks(app)

    def add_webvizstore(self) -> List[Tuple[Callable, List[Dict[str, Any]]]]:
        functions: List[Tuple[Callable, List[Dict[str, Any]]]] = [
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
        if self.csvfile_rft_ert is None:
            functions.append(
                (
                    load_csv,
                    [
                        {
                            "ensemble_paths": self.ens_paths,
                            "csv_file": "share/results/tables/rft_ert.csv",
                        },
                    ],
                )
            )
            try:
                load_csv(self.ens_paths, "share/results/tables/rft.csv")
                functions.append(
                    (
                        load_csv,
                        [
                            {
                                "ensemble_paths": self.ens_paths,
                                "csv_file": "share/results/tables/rft.csv",
                            },
                        ],
                    )
                )
            except KeyError:
                pass

        return functions

    @property
    def well_names(self) -> List[str]:
        return sorted(list(self.ertdatadf["WELL"].unique()))

    @property
    def zone_names(self) -> List[str]:
        return sorted(list(self.ertdatadf["ZONE"].unique()))

    @property
    def dates(self) -> List[str]:
        return sorted(list(self.ertdatadf["DATE"].unique()))

    def date_in_well(self, well: str) -> List[str]:
        df = self.ertdatadf.loc[self.ertdatadf["WELL"] == well]
        return [str(d) for d in list(df["DATE"].unique())]

    @property
    def ensembles(self) -> List[str]:
        return list(self.ertdatadf["ENSEMBLE"].unique())

    @property
    def enscolors(self) -> dict:
        return unique_colors(self.ensembles)

    def set_date_marks(self) -> Dict[str, Dict[str, Any]]:
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
    def formation_plot_selectors(self) -> List[html.Div]:
        return wcc.Selectors(
            label="Formation plot settings",
            children=[
                wcc.Dropdown(
                    label="Ensemble",
                    id=self.uuid("ensemble"),
                    options=[{"label": ens, "value": ens} for ens in self.ensembles],
                    value=self.ensembles[0],
                    multi=True,
                    clearable=False,
                ),
                wcc.Dropdown(
                    label="Well",
                    id=self.uuid("well"),
                    options=[
                        {"label": well, "value": well} for well in self.well_names
                    ],
                    value=self.well_names[0],
                    clearable=False,
                ),
                wcc.Dropdown(
                    label="Date",
                    id=self.uuid("date"),
                    options=[
                        {"label": date, "value": date}
                        for date in self.date_in_well(self.well_names[0])
                    ],
                    clearable=False,
                    value=self.date_in_well(self.well_names[0])[0],
                ),
                wcc.RadioItems(
                    label="Plot simulations as",
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
                ),
                wcc.RadioItems(
                    label="Depth option",
                    id=self.uuid("depth_option"),
                    options=[
                        {
                            "label": "TVD",
                            "value": "TVD",
                        },
                        {
                            "label": "MD",
                            "value": "MD",
                        },
                    ],
                    value="TVD",
                ),
            ],
        )

    @property
    def map_plot_selectors(self) -> List[html.Div]:

        return wcc.Selectors(
            label="Map plot settings",
            children=[
                wcc.Dropdown(
                    label="Ensemble",
                    id=self.uuid("map_ensemble"),
                    options=[
                        {"label": ens, "value": ens}
                        for ens in list(self.ertdatadf["ENSEMBLE"].unique())
                    ],
                    value=list(self.ertdatadf["ENSEMBLE"].unique())[0],
                    clearable=False,
                ),
                wcc.Dropdown(
                    label="Size points by",
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
                wcc.Dropdown(
                    label="Color points by",
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
                wcc.RangeSlider(
                    label="Filter date range",
                    id=self.uuid("map_date"),
                    min=self.ertdatadf["DATE_IDX"].min(),
                    max=self.ertdatadf["DATE_IDX"].max(),
                    value=[
                        self.ertdatadf["DATE_IDX"].min(),
                        self.ertdatadf["DATE_IDX"].max(),
                    ],
                    marks=self.date_marks,
                ),
            ],
        )

    def filter_layout(
        self, tab: str
    ) -> List[dash.development.base_component.Component]:
        """Layout for shared filters"""
        return wcc.Selectors(
            label="Selectors",
            children=[
                wcc.SelectWithLabel(
                    label="Ensembles",
                    size=min(4, len(self.ensembles)),
                    id=self.uuid(f"ensemble-{tab}"),
                    options=[{"label": name, "value": name} for name in self.ensembles],
                    value=self.ensembles,
                    multi=True,
                ),
                wcc.SelectWithLabel(
                    label="Wells",
                    size=min(20, len(self.well_names)),
                    id=self.uuid(f"well-{tab}"),
                    options=[
                        {"label": name, "value": name} for name in self.well_names
                    ],
                    value=self.well_names,
                    multi=True,
                ),
                wcc.SelectWithLabel(
                    label="Zones",
                    size=min(10, len(self.zone_names)),
                    id=self.uuid(f"zone-{tab}"),
                    options=[
                        {"label": name, "value": name} for name in self.zone_names
                    ],
                    value=self.zone_names,
                    multi=True,
                ),
                wcc.SelectWithLabel(
                    label="Dates",
                    size=min(10, len(self.dates)),
                    id=self.uuid(f"date-{tab}"),
                    options=[{"label": name, "value": name} for name in self.dates],
                    value=self.dates,
                    multi=True,
                ),
            ],
        )

    def size_color_layout(self) -> List[html.Div]:
        return wcc.Selectors(
            label="Plot settings",
            children=[
                wcc.Dropdown(
                    label="Color by",
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
                wcc.Dropdown(
                    label="Size by",
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
        )

    @property
    def layout(self) -> wcc.Tabs:

        return wcc.Tabs(
            children=[
                wcc.Tab(
                    label="RFT Map",
                    children=[
                        wcc.FlexBox(
                            children=[
                                wcc.Frame(
                                    style={"flex": 1, "height": "87vh"},
                                    children=[
                                        self.map_plot_selectors,
                                        self.formation_plot_selectors,
                                    ],
                                ),
                                wcc.Frame(
                                    style={"flex": 3, "height": "87vh"},
                                    color="white",
                                    highlight=False,
                                    children=wcc.Graph(
                                        id=self.uuid("map"),
                                    ),
                                ),
                                wcc.Frame(
                                    style={"flex": 3, "height": "87vh"},
                                    color="white",
                                    highlight=False,
                                    children=wcc.Graph(
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
                                ),
                            ]
                        )
                    ],
                ),
                wcc.Tab(
                    label="RFT misfit per real",
                    children=[
                        wcc.FlexBox(
                            children=[
                                wcc.Frame(
                                    style={"flex": 1, "height": "87vh"},
                                    children=self.filter_layout("misfitplot"),
                                ),
                                wcc.Frame(
                                    style={"flex": 6, "height": "87vh"},
                                    color="white",
                                    highlight=False,
                                    id=self.uuid("misfit-graph-wrapper"),
                                    children=[],
                                ),
                            ]
                        )
                    ],
                ),
                wcc.Tab(
                    label="RFT crossplot - sim vs obs",
                    children=[
                        wcc.FlexBox(
                            children=[
                                wcc.Frame(
                                    style={"flex": 1, "height": "87vh"},
                                    children=[
                                        self.filter_layout("crossplot"),
                                        self.size_color_layout(),
                                    ],
                                ),
                                wcc.Frame(
                                    style={"flex": 6, "height": "87vh"},
                                    color="white",
                                    highlight=False,
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
                wcc.Tab(
                    label="RFT misfit per observation",
                    children=[
                        wcc.FlexBox(
                            children=[
                                wcc.Frame(
                                    style={"flex": 1, "height": "87vh"},
                                    children=self.filter_layout("errorplot"),
                                ),
                                wcc.Frame(
                                    color="white",
                                    highlight=False,
                                    style={"flex": 6, "height": "87vh"},
                                    children=wcc.Graph(
                                        style={"height": "84vh"},
                                        id=self.uuid("errorplot-graph"),
                                    ),
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )

    def set_callbacks(self, app: dash.Dash) -> None:
        @app.callback(
            Output(self.uuid("well"), "value"),
            [
                Input(self.uuid("map"), "clickData"),
            ],
        )
        def _get_clicked_well(click_data: Dict[str, List[Dict[str, Any]]]) -> str:
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
        def _update_map(
            ensemble: str, sizeby: str, colorby: str, dates: List[float]
        ) -> Dict[str, Any]:
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
                Input(self.uuid("depth_option"), "value"),
            ],
        )
        def _update_formation_plot(
            well: str, date: str, ensembles: List[str], linetype: str, depth_option: str
        ) -> Dict[str, Any]:
            if date not in self.date_in_well(well):
                raise PreventUpdate

            figure = FormationFigure(
                well=well,
                ertdf=self.ertdatadf,
                enscolors=self.enscolors,
                depth_option=depth_option,
                date=date,
                ensembles=ensembles,
                simdf=self.simdf,
                obsdf=self.obsdatadf,
            )

            if self.formations is not None:
                figure.add_formation(self.formationdf)

            figure.add_simulated_lines(linetype)
            figure.add_additional_observations()
            figure.add_ert_observed()

            return {
                "data": figure.traces,
                "layout": figure.layout,
            }

        @app.callback(
            Output(self.uuid("linetype"), "options"),
            Output(self.uuid("linetype"), "value"),
            Input(self.uuid("depth_option"), "value"),
            State(self.uuid("linetype"), "value"),
            State(self.uuid("well"), "value"),
            State(self.uuid("date"), "value"),
        )
        def _update_linetype(
            depth_option: str,
            current_linetype: str,
            current_well: str,
            current_date: str,
        ) -> Tuple[List[Dict[str, str]], str]:
            if self.simdf is not None:
                df = filter_frame(
                    self.simdf,
                    {"WELL": current_well, "DATE": current_date},
                )
                if depth_option == "TVD" or (
                    depth_option == "MD"
                    and "CONMD" in self.simdf
                    and len(df["CONMD"].unique()) == len(df["DEPTH"].unique())
                ):

                    return [
                        {
                            "label": "Realization lines",
                            "value": "realization",
                        },
                        {
                            "label": "Statistical fanchart",
                            "value": "fanchart",
                        },
                    ], current_linetype

            return [
                {
                    "label": "Realization lines",
                    "value": "realization",
                },
            ], "realization"

        @app.callback(
            [Output(self.uuid("date"), "options"), Output(self.uuid("date"), "value")],
            [
                Input(self.uuid("well"), "value"),
            ],
            [State(self.uuid("date"), "value")],
        )
        def _update_date(
            well: str, current_date: str
        ) -> Tuple[List[Dict[str, str]], str]:
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
        def _misfit_plot(
            wells: List[str], zones: List[str], dates: List[str], ensembles: List[str]
        ) -> List[wcc.Graph]:
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
        def _crossplot(
            wells: List[str],
            zones: List[str],
            dates: List[str],
            ensembles: List[str],
            sizeby: str,
            colorby: str,
        ) -> List[wcc.Graph]:
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
        def _errorplot(
            wells: List[str], zones: List[str], dates: List[str], ensembles: List[str]
        ) -> Dict[str, Union[list, dict]]:
            df = filter_frame(
                self.ertdatadf,
                {"WELL": wells, "ZONE": zones, "DATE": dates, "ENSEMBLE": ensembles},
            )
            return update_errorplot(df, self.enscolors)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file: str) -> pd.DataFrame:
    return pd.read_csv(csv_file)
