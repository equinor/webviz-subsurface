from typing import Optional, List, Dict, Tuple, Callable, Any
import json
import itertools
import io

import numpy as np
import pandas as pd
import dash
from dash.dependencies import Input, Output
import dash_html_components as html
import dash_core_components as dcc

import webviz_core_components as wcc
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore
from webviz_config import WebvizPluginABC
from webviz_config import WebvizSettings
import webviz_subsurface_components

from .._datainput.fmu_input import load_csv
from .._datainput.well_completions import read_zone_layer_mapping, read_well_attributes


class WellCompletions(WebvizPluginABC):
    """Visualizes well completions data per well coming from export of the Eclipse COMPDAT output. \
    Data is grouped per well and zone and can be filtered accoring to flexible well categories.

    ---

    * **`ensembles`:** Which ensembles in `shared_settings` to visualize.
    * **`compdat_file`:** csvfile with compdat data per realization
    * **`zone_layer_mapping_file`:** Lyr file specifying the zone->layer mapping \
    * **`well_attributes_file`:** Json file with categorical well attributes \
    * **`kh_unit`:** Will normally be mDm
    * **`kh_decimal_places`:**

    ---
    The minimum requirement is to define `ensembles`.

    **COMPDAT input**

    `compdat_file` is a path to a file stored per realization (e.g. in \
    `share/results/wells/compdat.csv`.

    The `compdat_file` file can be dumped to disk per realization by a forward model in ERT that
    wraps the command `ecl2csv compdat input_file -o output_file` (requires that you have `ecl2df`
    installed).
    [Link to ecl2csv compdat documentation.](https://equinor.github.io/ecl2df/usage/compdat.html)

    **Zone layer mapping**

    `zone_layer_mapping_file` file can be dumped to disk per realization by an internal \
    RMS script as part of the FMU workflow. A sample python script will be made available.

    The file needs to be on the lyr format used in ResInsight.
    [Link to description of lyr format](https://resinsight.org/3d-main-window/formations/#formation-names-description-files-_lyr_).

    If no file exists, layers will be used as zones.

    **Well Attributes file**

    `well_attributes_file` file is intended to be generated per realization by an internal \
    RMS script as part of the FMU workflow. A sample script will be made available, but it is \
    possible to manually set up the file and copy it to the correct folder on the scratch disk.\
    The categorical well attributes are completely flexible.

    The file should be a json file on the following format:
    ```json
    {
        "version" : "0.1",
        "wells" : [
        {
            "alias" : {
                "eclipse" : "OP_1"
            },
            "attributes" : {
                "mlt_singlebranch" : "mlt",
                "structure" : "East",
                "welltype" : "producer"
            },
            "name" : "OP_1"
        },
        {
            "alias" : {
                "eclipse" : "GI_1"
            },
            "attributes" : {
                "mlt_singlebranch" : "singlebranch",
                "structure" : "West",
                "welltype" : "gas injector"
            },
            "name" : "GI_1"
        },
        ]
    }
    ```
    """  # pylint: disable=line-too-long

    def __init__(
        self,
        app: dash.Dash,
        webviz_settings: WebvizSettings,
        ensembles: list,
        compdat_file: str = "share/results/wells/compdat.csv",
        zone_layer_mapping_file: str = "rms/output/zone/simgrid_zone_layer_mapping.lyr",
        well_attributes_file: str = "rms/output/wells/well_attributes.json",
        kh_unit: str = "",
        kh_decimal_places: int = 2,
    ):
        # pylint: disable=too-many-arguments
        super().__init__()
        self.theme = webviz_settings.theme
        self.compdat_file = compdat_file
        self.zone_layer_mapping_file = zone_layer_mapping_file
        self.well_attributes_file = well_attributes_file
        self.ensembles = ensembles
        self.kh_unit = kh_unit
        self.kh_decimal_places = kh_decimal_places

        self.colors = self.theme.plotly_theme["layout"]["colorway"]
        self.ens_paths = {
            ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
            for ens in ensembles
        }

        self.set_callbacks(app)

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        return [
            (
                create_ensemble_dataset,
                [
                    {
                        "ensemble": ensemble,
                        "ensemble_path": self.ens_paths[ensemble],
                        "compdat_file": self.compdat_file,
                        "zone_layer_mapping_file": self.zone_layer_mapping_file,
                        "well_attributes_file": self.well_attributes_file,
                        "colors": self.colors,
                        "kh_unit": self.kh_unit,
                        "kh_decimal_places": self.kh_decimal_places,
                    }
                    for ensemble in self.ensembles
                ],
            ),
        ]

    @property
    def tour_steps(self) -> list:
        return [
            {
                "id": self.uuid("layout"),
                "content": "Dashboard vizualizing Eclipse well completion output.",
            },
            {"id": self.uuid("ensemble_dropdown"), "content": "Select ensemble."},
            {
                "id": self.uuid("well_completions_wrapper"),
                "content": (
                    "Visualization of the well completions. "
                    "Time slider for selecting which time steps to display. "
                    "Different vizualisation and filtering alternatives are available "
                    "in the upper right corner."
                ),
            },
        ]

    @property
    def layout(self) -> html.Div:
        return html.Div(
            id=self.uuid("layout"),
            children=[
                wcc.FlexBox(
                    children=[
                        html.Div(
                            style={"flex": "1", "padding": "10px"},
                            children=html.Label(
                                children=[
                                    html.Span(
                                        "Ensemble", style={"font-weight": "bold"}
                                    ),
                                    dcc.Dropdown(
                                        id=self.uuid("ensemble_dropdown"),
                                        options=[
                                            {"label": ens, "value": ens}
                                            for ens in self.ensembles
                                        ],
                                        clearable=False,
                                        value=self.ensembles[0],
                                        persistence=True,
                                        persistence_type="session",
                                    ),
                                ]
                            ),
                        ),
                        html.Div(style={"flex": 4}),
                    ],
                ),
                html.Div(
                    id=self.uuid("well_completions_wrapper"),
                ),
            ],
        )

    def set_callbacks(self, app: dash.Dash) -> None:
        @app.callback(
            Output(self.uuid("well_completions_wrapper"), "children"),
            Output(self.uuid("well_completions_wrapper"), "style"),
            Input(self.uuid("ensemble_dropdown"), "value"),
        )
        def _render_well_completions(ensemble_name: str) -> list:

            data = json.load(
                create_ensemble_dataset(
                    ensemble_name,
                    self.ens_paths[ensemble_name],
                    self.compdat_file,
                    self.zone_layer_mapping_file,
                    self.well_attributes_file,
                    self.colors,
                    self.kh_unit,
                    self.kh_decimal_places,
                )
            )
            zones = len(data["stratigraphy"])
            return [
                webviz_subsurface_components.WellCompletions(
                    id="well_completions", data=data
                ),
                {"padding": "10px", "height": zones * 50 + 180, "min-height": 500},
            ]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def create_ensemble_dataset(
    ensemble: str,
    ensemble_path: str,
    compdat_file: str,
    zone_layer_mapping_file: str,
    well_attributes_file: str,
    colors: list,
    kh_unit: str,
    kh_decimal_places: int,
) -> io.BytesIO:
    # pylint: disable=too-many-locals
    """Creates the well completion data set for the WellCompletions component

    Returns a dictionary on a given format specified here:
    https://github.com/equinor/webviz-subsurface-components/blob/master/inputSchema/wellCompletions.json
    """
    df = load_csv(ensemble_paths={ensemble: ensemble_path}, csv_file=compdat_file)
    qc_compdat(df)
    layer_zone_mapping = read_zone_layer_mapping(
        ensemble_path=ensemble_path,
        zone_layer_mapping_file=zone_layer_mapping_file,
    )
    well_attributes = read_well_attributes(
        ensemble_path=ensemble_path,
        well_attributes_file=well_attributes_file,
    )

    time_steps = sorted(df.DATE.unique())
    realizations = list(sorted(df.REAL.unique()))
    layers = np.sort(df.K1.unique())

    if layer_zone_mapping is None:
        # use layers as zones
        layer_zone_mapping = {layer: f"Layer{layer}" for layer in layers}

    df["ZONE"] = df.K1.map(layer_zone_mapping)
    zone_names = list(dict.fromkeys(layer_zone_mapping.values()))

    result = {
        "version": "1.0.0",
        "units": {"kh": {"unit": kh_unit, "decimalPlaces": kh_decimal_places}},
        "stratigraphy": extract_stratigraphy(layer_zone_mapping, colors),
        "timeSteps": time_steps,
        "wells": extract_wells(
            df, zone_names, time_steps, realizations, well_attributes
        ),
    }

    return io.BytesIO(json.dumps(result).encode())


def qc_compdat(compdat: pd.DataFrame) -> None:
    """QCs that the compdat data has the required format"""
    needed_columns = ["WELL", "K1", "OP/SH", "KH"]
    for column in needed_columns:
        if column not in compdat:
            raise ValueError(
                f"Column {column} not found in compdat dataframe."
                "This should not occur unless there has been changes to ecl2df."
            )


def get_time_series(df: pd.DataFrame, time_steps: list) -> tuple:
    """Create two lists with values for each time step
    * the first one is on the form [0,0,0,1,1,1,1,-1,-1,-1] where '0' means no event,\
    '1' is open, '-1' is shut.
    * the second is with sum of kh values for the open compdats in each zone

    The input data frame is assumed to contain data for single well,
    single zone and single realization.
    """
    if df.empty:
        return [0] * len(time_steps), [0] * len(time_steps)

    events, kh_values = [], []
    event_value, kh_value = 0, 0

    for timestep in time_steps:
        if timestep in df.DATE.unique():
            df_timestep = df[df.DATE == timestep]
            df_timestep_open = df_timestep[df_timestep["OP/SH"] == "OPEN"]

            # if minimum one of the compdats for the zone is OPEN then the zone is considered open
            event_value = 1 if not df_timestep_open.empty else -1
            kh_value = df_timestep_open.KH.sum()

        events.append(event_value)
        kh_values.append(kh_value)
    return events, kh_values


def get_completion_events_and_kh(
    df: pd.DataFrame, zone_names: list, time_steps: list
) -> tuple:
    """Extracts completion events ad kh values into two lists of lists of lists,
    one with completions events and one with kh values
    * Axis 0 is realization
    * Axis 1 is zone
    * Axis 2 is time step
    """
    compl_events, kh_values = [], []
    for _, realdata in df.groupby("REAL"):
        compl_events_real, kh_real = [], []
        for zone_name in zone_names:
            zone_data = realdata[realdata.ZONE == zone_name]
            compl_events_real_zone, kh_real_zone = get_time_series(
                zone_data, time_steps
            )
            compl_events_real.append(compl_events_real_zone)
            kh_real.append(kh_real_zone)

        compl_events.append(compl_events_real)
        kh_values.append(kh_real)
    return compl_events, kh_values


def format_time_series(
    open_frac: List[float],
    shut_frac: List[float],
    kh_mean: List[float],
    kh_min: List[float],
    kh_max: List[float],
) -> Optional[Dict]:
    """The functions takes in five lists with values per timestep
    * fractions of realizations open in this zone
    * fractions of realizations shut in this zone
    * kh mean over open realizations
    * kh min over open realizations
    * kh max over open realizations

    Returns the data in compact form:
    {
        t: [3, 5],
        open: [0.25, 1.0],
        shut: [0.75, 0.0],
        khMean: [500, 1000],
        khMin: [200, 800],
        khMean: [600, 1500]
    }
    """
    output: Dict[str, list] = {
        "t": [],
        "open": [],
        "shut": [],
        "khMean": [],
        "khMin": [],
        "khMax": [],
    }
    prev_open_val = prev_shut_val = 0.0

    for i, _ in enumerate(open_frac):
        open_val = open_frac[i]
        shut_val = shut_frac[i]
        if open_val != prev_open_val or shut_val != prev_shut_val:
            output["t"].append(i)
            output["open"].append(open_val)
            output["shut"].append(shut_val)
            output["khMean"].append(kh_mean[i])
            output["khMin"].append(kh_min[i])
            output["khMax"].append(kh_max[i])
        prev_open_val = open_val
        prev_shut_val = shut_val
    return output


def calc_over_realizations(
    compl_events: list, kh_values: list, realizations: list
) -> tuple:
    # pylint: disable=assignment-from-no-return
    """Takes in two three dimensional lists where the levels are: 1. realization \
    2. zones and 3. timesteps

    Returns two dimensional lists where calculations have been done over the \
    realization level.
    """
    # calculate fraction of open realizations
    open_count = np.maximum(np.asarray(compl_events), 0)  # remove -1
    open_count_reduced = open_count.sum(axis=0)  # sum over realizations
    open_frac = (
        np.asarray(open_count_reduced, dtype=np.float64) / float(len(realizations))
    ).round(decimals=3)

    # calculate fraction of shut realizations
    shut_count = (
        np.minimum(np.asarray(compl_events), 0) * -1
    )  # remove +1 and convert -1 to 1
    shut_count_reduced = shut_count.sum(axis=0)  # sum over realizations
    shut_frac = (
        np.asarray(shut_count_reduced, dtype=np.float64) / float(len(realizations))
    ).round(decimals=3)

    # calculate khMean, khMin and khMax
    np_kh_values = np.asarray(kh_values)
    kh_mean = (np_kh_values.sum(axis=0) / float(len(realizations))).round(decimals=2)
    kh_min = np_kh_values.min(axis=0).round(decimals=2)
    kh_max = np_kh_values.max(axis=0).round(decimals=2)

    return open_frac, shut_frac, kh_mean, kh_min, kh_max


def extract_well(
    df: pd.DataFrame, well: str, zone_names: list, time_steps: list, realizations: list
) -> Dict[str, Any]:
    # pylint: disable=too-many-locals
    """Extract completion events and kh values for a single well"""
    well_dict: Dict[str, Any] = {}
    well_dict["name"] = well

    compl_events, kh_values = get_completion_events_and_kh(df, zone_names, time_steps)
    open_frac, shut_frac, kh_mean, kh_min, kh_max = calc_over_realizations(
        compl_events, kh_values, realizations
    )
    result = {}
    for (
        zone_name,
        open_frac_zone,
        shut_frac_zone,
        kh_mean_zone,
        kh_min_zone,
        kh_max_zone,
    ) in zip(zone_names, open_frac, shut_frac, kh_mean, kh_min, kh_max):
        if list(open_frac_zone):
            result[zone_name] = format_time_series(
                open_frac_zone, shut_frac_zone, kh_mean_zone, kh_min_zone, kh_max_zone
            )
    well_dict["completions"] = result
    return well_dict


def extract_wells(
    df: pd.DataFrame,
    zone_names: list,
    time_steps: list,
    realizations: list,
    well_attributes: Optional[dict],
) -> list:
    """Generates the wells part of the input dictionary to the WellCompletions component"""
    well_list = []
    for well_name, well_group in df.groupby("WELL"):
        well_data = extract_well(
            well_group, well_name, zone_names, time_steps, realizations
        )
        well_data["attributes"] = (
            well_attributes[well_name]
            if (well_attributes is not None and well_name in well_attributes)
            else {}
        )
        well_list.append(well_data)
    return well_list


def extract_stratigraphy(layer_zone_mapping: dict, colors: list) -> list:
    """Returns the stratigraphy part of the data set"""
    color_iterator = itertools.cycle(colors)
    return [
        {"name": zone, "color": next(color_iterator)}
        for zone in dict.fromkeys(layer_zone_mapping.values())
    ]
