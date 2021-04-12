import json
import pandas as pd
import numpy as np
import random

import dash
from dash.dependencies import Input, Output
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore

import webviz_subsurface_components
from webviz_config import WebvizPluginABC
from webviz_config import WebvizSettings

from .._datainput.fmu_input import load_csv


class WellCompletions(WebvizPluginABC):
    """Visualizes well completions from Eclipse compdat data

    ---

    * **`ensembles`:** Which ensembles in `shared_settings` to visualize.
    * **'compdatfile:** compdatfile
    * **`layer_to_zone_map`:** A file specifying the stratigraphy

    ---
    The minimum requirement is to define `ensembles`.

    If no `layer_to_zone_map` is defined then ...

    `compdatfile` is a path to a file stored per realization (e.g. in \
    `share/results/wells/compdat.csv`).

    The `compdatfile` file can e.g. be dumped to disk per realization by a forward model in ERT that
    wraps the command `ecl2csv compdat input_file -o output_file` (requires that you have `ecl2df`
    installed).
    [Link to ecl2csv compdat documentation.](https://equinor.github.io/ecl2df/usage/compdat.html)

    """

    def __init__(
        self,
        app: dash.Dash,
        webviz_settings: WebvizSettings,
        ensembles: list,
        compdatfile: str = "share/results/wells/compdat.csv",
        stratigraphy: str = None
    ):
        super().__init__()
        self.compdatfile = compdatfile
        self.stratigraphy = stratigraphy
        self.ensembles = ensembles
        self.ens_paths = {
            ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
            for ens in ensembles
        }
        self.compdat = load_csv(ensemble_paths=self.ens_paths, csv_file=compdatfile)
        self.qc_compdat()
        random.seed(1234) #to get the same colors
        self.stratigraphy = {
            "Stoe":{
                "from_layer":1,
                "to_layer":15
            },
            "Nordmela":{
                "from_layer":16,
                "to_layer":90
            }
        }
        #qc stratigraphy (overlap etc) ?

        #CACHE data at start-up
        for ens in self.ensembles:
            output = self.create_ensemble_dataset(ens)

        self.set_callbacks(app)

    def add_webvizstore(self):
        return (
            [
                (
                    load_csv,
                    [
                        {"ensemble_paths":self.ens_paths},
                        {"csv_file":self.compdatfile}
                    ],
                )
            ]
        )

    def qc_compdat(self):
        """
        QCs that the compdat data has the required format
        """
        needed_columns = ["WELL", "K1", "OP/SH", "KH"]
        for column in needed_columns:
            if column not in self.compdat:
                raise ValueError(
                    f"""
                    Column {column} not found in compdat dataframe.
                    This should not occur unless there has been changes to ecl2df.
                    """
                )


    @property
    def layout(self) -> html.Div:
        return html.Div(
            children=[
                wcc.FlexBox(
                    children=[
                        html.Div(
                            style={"flex": "1", "padding":"10px"},
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
                        html.Div(
                            style={"flex":4}
                        )
                    ],
                ),
                html.Div(
                    id=self.uuid("well_completions_wrapper"),
                    #style={"height": 600},
                    style={"padding": "10px", "height":600},
                ),
            ]
        )

    def set_callbacks(self, app):
        @app.callback(
            [
                Output(self.uuid("well_completions_wrapper"), "children"),
            ],
            [
                Input(self.uuid("ensemble_dropdown"), "value"),
            ],
        )
        def _render_well_completions(ensemble_name):

            data = self.create_ensemble_dataset(ensemble_name)

            return [
                webviz_subsurface_components.WellCompletions(
                    id="well_completions", data=data
                )
            ]

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def create_ensemble_dataset(self, ensemble):
        """
        Creates the well completion data set for the WellCompletions component
        Returns a dictionary with given format
        """
        df = self.compdat[self.compdat.ENSEMBLE == ensemble]

        time_steps = sorted(df.DATE.unique())
        realisations = np.asarray(sorted(df.REAL.unique()), dtype=np.int32)
        layers = np.sort(df.K1.unique())
        #layer_to_zone_map = get_layer_to_zone_map(layers, self.stratigraphy)

        result = {}
        result["version"] = "1.0.0"
        result["stratigraphy"] = extract_stratigraphy(self.stratigraphy)
        result["timeSteps"] = time_steps

        zone_names = list(self.stratigraphy.keys()) # [a["name"] for a in result["stratigraphy"]]
        result["wells"] = extract_wells(
            df, self.stratigraphy, zone_names, time_steps, realisations,
        )
        #with open("/private/olind/webviz/result.json", "w") as f:
        #    json.dump(result, f)

        return result

def get_zone_for_layer(layer, stratigraphy):
    for zone_attr in stratigraphy:
        if zone_attr["from_layer"] <= layer <= zone_attr["to_layer"]:
            return zone_attr["name"]
    raise ValueError(f"No zone found for layer {layer}")

def get_layer_to_zone_map(layers, stratigraphy):
    layer_to_zone_map = {}
    for layer in layers:
        layer_to_zone_map[layer] = get_zone_for_layer(layer, stratigraphy)
    return layer_to_zone_map

def get_time_series(df, time_steps):
    """
    Creates a time series with a value for each time step in the form
    [0,0,0,1,1,1,1,-1,-1,-1]
    '0' means no event, '1' is open, '-1' is shut.
    The input data frame is assumed to contain data for single well,
    single zone, single realisation.
    """
    if df.shape[0] == 0:
        return [0] * len(time_steps)

    result = []
    event_value = 0

    for t in time_steps:
        if t in df.DATE.unique():
            df_timestep = df[df.DATE==t]
            df_timestep_open = df_timestep[df["OP/SH"]=="OPEN"]

            #if minimum one of the compdats for the zone is OPEN then the zone is considered open
            event_value = 1 if len(df_timestep_open)>0 else -1

        result.append(event_value)
    return result


def get_completions(df, stratigraphy, time_steps, realisations):
    """
    Extracts completions into a lists of list
    Full matrix - every time step and realisation
    """
    completions = []
    for rname, realdata in df.groupby("REAL"):
        real = []
        for zone_name, zone_attr in stratigraphy.items():
            data = realdata.loc[(realdata.K1>=zone_attr["from_layer"]) & (realdata.K1<=zone_attr["to_layer"])]
            real.append(get_time_series(data, time_steps))

        completions.append(real)
    return completions


def format_time_series(time_series):
    """
    The function compresses the fraction of completed realisation into a more compact form:
    [0, 0, 0, 0.25, 0.25, 1.0, 1.0] -> { t: [3, 5], f: [0.25, 1.0] }
    t is a list of list of time steps where the fraction changes,
    f is the corresponding open fraction.
    """
    time_steps = []
    values = []
    n = len(time_series)
    v0 = time_series[0]
    if v0 > 0.0:
        time_steps.append(0)
        values.append(v0)
    for i in range(1, n):
        v = time_series[i]
        if v != v0:
            time_steps.append(i)
            values.append(v)
            v0 = v

    if len(time_steps) == 0:
        return None
    r = {}
    r["t"] = time_steps
    r["f"] = values
    return r


def extract_well(df, well, stratigraphy, zone_names, time_steps, realisations):
    """
    Extract completion data for a single well
    """
    well_dict = {}
    well_dict["name"] = well

    completions = get_completions(df, stratigraphy, time_steps, realisations)
    # get rid of negative "shut" values
    open_count = np.maximum(np.asarray(completions), 0)
    # sum over realisations
    open_count_reduced = open_count.sum(axis=0)
    # calculate fraction of open realisations
    open_frac = np.asarray(open_count_reduced, dtype=np.float64) / float(
        len(realisations)
    )

    result = {}
    for zone_name, time_series in zip(zone_names, open_frac):
        r = format_time_series(time_series)
        if r is not None:
            result[zone_name] = r
    well_dict["completions"] = result

    attributes = {}
    attributes["type"] = "Producer"
    attributes["region"] = "SomeRegion"
    well_dict["attributes"] = attributes
    return well_dict


def extract_wells(df, stratigraphy, zone_names, time_steps, realisations):
    """
    Generates the wells part of the input dictionary to the WellCompletions component
    """
    well_list = []
    for name, well_group in df.groupby("WELL"):
        well_list.append(
            extract_well(well_group, name, stratigraphy, zone_names, time_steps, realisations)
        )
    return well_list


def random_color_str():
    """
    Returns a random colo
    """
    r = random.randint(8, 15)  # nosec - bandit B311
    g = random.randint(8, 15)  # nosec - bandit B311
    b = random.randint(8, 15)  # nosec - bandit B311
    s = hex((r << 8) + (g << 4) + b)
    return "#" + s[-3:]


def extract_stratigraphy(stratigraphy):
    """
    Returns the stratigraphy part of the data set
    """
    result = []
    for zone_name, zone_attr in stratigraphy.items():
        zdict = {}
        zdict["name"] = zone_name
        zdict["color"] = random_color_str()
        result.append(zdict)
    return result
