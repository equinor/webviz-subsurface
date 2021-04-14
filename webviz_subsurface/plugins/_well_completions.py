import json
import pandas as pd
import numpy as np
import itertools

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
        self.theme = webviz_settings.theme
        self.colors = [ls[1] for ls in self.theme.plotly_theme["layout"]["colorscale"]["sequential"]]
        #self.colors = self.theme.plotly_theme["layout"]["colorway"]
        #print(self.colors)
        self.compdatfile = compdatfile
        self.stratigraphy = stratigraphy
        self.ensembles = ensembles
        self.ens_paths = {
            ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
            for ens in ensembles
        }
        self.compdat = load_csv(ensemble_paths=self.ens_paths, csv_file=compdatfile)
        self.qc_compdat()
        self.stratigraphy = {
            "Stoe4":{
                "from_layer":1,
                "to_layer":5
            },
            "Stoe3.2":{
                "from_layer":6,
                "to_layer":6
            },
            "Stoe3.1":{
                "from_layer":7,
                "to_layer":12
            },
            "Stoe2":{
                "from_layer":13,
                "to_layer":19
            },
            "Stoe1":{
                "from_layer":20,
                "to_layer":25
            },
            "Nordmela3":{
                "from_layer":26,
                "to_layer":34
            },
            "Nordmela2":{
                "from_layer":35,
                "to_layer":54
            },
            "Nordmela1":{
                "from_layer":55,
                "to_layer":60
            },
            "Tubaaen3":{
                "from_layer":61,
                "to_layer":71
            },
            "Tubaaen2":{
                "from_layer":72,
                "to_layer":78
            },
            "Tubaaen1":{
                "from_layer":79,
                "to_layer":90
            },
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
                ),
            ]
        )

    def set_callbacks(self, app):
        @app.callback(
            [
                Output(self.uuid("well_completions_wrapper"), "children"),
                Output(self.uuid("well_completions_wrapper"), "style"),
            ],
            [
                Input(self.uuid("ensemble_dropdown"), "value"),
            ],
        )
        def _render_well_completions(ensemble_name):

            data = self.create_ensemble_dataset(ensemble_name)
            zones = len(data["stratigraphy"])
            return [
                webviz_subsurface_components.WellCompletions(
                    id="well_completions", data=data
                ),
                {"padding":"10px", "height":zones*50}
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
        result["stratigraphy"] = extract_stratigraphy(self.stratigraphy, self.colors)
        result["timeSteps"] = time_steps

        zone_names = list(self.stratigraphy.keys()) # [a["name"] for a in result["stratigraphy"]]
        result["wells"] = extract_wells(
            df, self.stratigraphy, zone_names, time_steps, realisations,
        )
        with open("/private/olind/webviz/result.json", "w") as f:
           json.dump(result, f)

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
    Create two lists with values for each time step
    * the first one is on the form [0,0,0,1,1,1,1,-1,-1,-1] where '0' means no event, '1' is open, '-1' is shut.
    * the second is with sum of kh values for the open compdats in each zone

    The input data frame is assumed to contain data for single well,
    single zone and single realisation.
    """
    if df.shape[0] == 0:
        return [0] * len(time_steps), [0] * len(time_steps)

    events, kh = [], []
    event_value, kh_value = 0, 0

    for t in time_steps:
        if t in df.DATE.unique():
            df_timestep = df[df.DATE==t]
            df_timestep_open = df_timestep[df_timestep["OP/SH"]=="OPEN"]

            #if minimum one of the compdats for the zone is OPEN then the zone is considered open
            event_value = 1 if len(df_timestep_open)>0 else -1
            kh_value = df_timestep_open.KH.sum()

        events.append(event_value)
        kh.append(kh_value)
    return events, kh


def get_completion_events_and_kh(df, stratigraphy, time_steps, realisations):
    """
    Extracts completion events ad kh values into two lists of lists of lists,
    one with completions events and one with kh values
    * Axis 0 is realization
    * Axis 1 is zone
    * Axis 2 is time step
    """
    compl_events, kh = [], []
    for rname, realdata in df.groupby("REAL"):
        compl_events_real, kh_real = [], []
        for zone_name, zone_attr in stratigraphy.items():
            data = realdata.loc[(realdata.K1>=zone_attr["from_layer"]) & (realdata.K1<=zone_attr["to_layer"])]
            compl_events_real_zone, kh_real_zone = get_time_series(data, time_steps)
            compl_events_real.append(compl_events_real_zone)
            kh_real.append(kh_real_zone)

        compl_events.append(compl_events_real)
        kh.append(kh_real)
    return compl_events, kh


def format_time_series(open_frac, shut_frac, ls_khmean, ls_khmin, ls_khmax):
    """
    The functions takes in two lists
    * list with fractions of realisations open in this zone, for each timestep
    * list with fractions of realisations shut in this zone, for each timestep

    Returns the data in compact form:
    * {t: [3, 5], open: [0.25, 1.0], shut: [0.75, 0.0]}
    """
    time_steps, open_values, shut_values, khmean_values, khmin_values, khmax_values = [], [], [], [], [], []
    prev_open_value, prev_shut_value, prev_khmean, prev_khmin, prev_khmax = 0, 0, 0, 0, 0

    for i, (open_value, shut_value, khmean, khmin, khmax) in enumerate(zip(open_frac, shut_frac, ls_khmean, ls_khmin, ls_khmax)):
        conditions = [
            open_value != prev_open_value,
            shut_value != prev_shut_value,
            khmean != prev_khmean,
            khmin != prev_khmin,
            khmax != prev_khmax
        ]
        if any(conditions):
            time_steps.append(i)
            open_values.append(open_value)
            shut_values.append(shut_value)
            khmean_values.append(khmean)
            khmin_values.append(khmin)
            khmax_values.append(khmax)
        prev_open_value = open_value
        prev_shut_value = shut_value
        prev_khmean = khmean
        prev_khmin = khmin
        prev_khmax = khmax
    if len(time_steps) == 0:
        return None
    r = {}
    r["t"] = time_steps
    r["open"] = open_values
    r["shut"] = shut_values
    r["khMean"] = khmean_values
    r["khMin"] = khmin_values
    r["khMax"] = khmax_values
    return r


def extract_well(df, well, stratigraphy, zone_names, time_steps, realisations):
    """
    Extract completion data for a single well
    """
    well_dict = {}
    well_dict["name"] = well

    compl_events, kh = get_completion_events_and_kh(df, stratigraphy, time_steps, realisations)

    # calculate fraction of open realizations
    open_count = np.maximum(np.asarray(compl_events), 0)     # remove -1
    open_count_reduced = open_count.sum(axis=0)             # sum over realizations
    open_frac = np.asarray(open_count_reduced, dtype=np.float64) / float(
        len(realisations)
    )

    # calculate fraction of shut realizations
    shut_count = np.minimum(np.asarray(compl_events), 0)*-1  # remove 1 and convert -1 to 1
    shut_count_reduced = shut_count.sum(axis=0)             # sum over realizations
    shut_frac = np.asarray(shut_count_reduced, dtype=np.float64) / float(
        len(realisations)
    )

    # calculate khMean, khMin and khMax
    kh_mean = np.asarray(kh).sum(axis=0) / float(
        len(realisations)
    )
    kh_min = kh_mean #must be implemented
    kh_max = kh_mean #must be implemented

    result = {}
    for zone_name, open_frac_zone, shut_frac_zone, kh_mean_zone, kh_min_zone, kh_max_zone in zip(zone_names, open_frac, shut_frac, kh_mean, kh_min, kh_max):
        r = format_time_series(open_frac_zone, shut_frac_zone, kh_mean_zone, kh_min_zone, kh_max_zone)
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

def parse_rgb(rgbstr):
    rgbstr = rgbstr.replace("rgb", "").replace("(","").replace(")", "")
    (r, g, b) = (int(val) for val in rgbstr.split(","))
    s = hex((r << 8) + (g << 4) + b)
    return "#" + s[-3:]

def extract_stratigraphy(stratigraphy, colors):
    """
    Returns the stratigraphy part of the data set
    """
    color_iterator = itertools.cycle(colors)
    result = []
    for zone_name, zone_attr in stratigraphy.items():
        zdict = {}
        zdict["name"] = zone_name
        zdict["color"] = parse_rgb(next(color_iterator))
        result.append(zdict)
    return result
