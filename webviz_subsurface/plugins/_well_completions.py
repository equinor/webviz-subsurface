import json
import pandas as pd
import numpy as np
import itertools
import io


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
import ecl2df


class WellCompletions(WebvizPluginABC):
    """Visualizes well completions data per well coming from export of the Eclipse COMPDAT output. \
    Data is grouped per well and zone and can be filtered accoring to flexible well categories.

    ---

    * **`ensembles`:** Which ensembles in `shared_settings` to visualize.
    * **`compdatfile`:** csvfile with compdat data per realization
    * **`layer_to_zone_mapping_file`:** lyr file specifying the zone->layer mapping (also per realization)
    * **`well_attributes_file`:** Optional json file specifying generic well categorical attributes

    ---
    The minimum requirement is to define `ensembles`.

    **COMPDAT input**

    `compdatfile` is a path to a file stored per realization (e.g. in \
    `share/results/wells/compdat.csv`.

    The `compdatfile` file can be dumped to disk per realization by a forward model in ERT that
    wraps the command `ecl2csv compdat input_file -o output_file` (requires that you have `ecl2df`
    installed).
    [Link to ecl2csv compdat documentation.](https://equinor.github.io/ecl2df/usage/compdat.html)

    ** Layer to zone mapping **

    `layer_to_zone_mapping_file` file can be dumped to disk per realization by an internal \
    RMS script as part of the FMU workflow. A sample python script should be available in the \
    Drogon project:  export_zone_layer_mapping.py

    The file needs to be on the lyr format used in Resinsight.
    [Link to description of lyr format.](https://resinsight.org/3d-main-window/formations/#formation-names-description-files-_lyr_)

    ** Well Attributes file **

    Description and example needed
    """

    def __init__(
        self,
        app: dash.Dash,
        webviz_settings: WebvizSettings,
        ensembles: list,
        compdatfile: str = "share/results/wells/compdat.csv",
        zone_layer_mapping_file: str = "share/results/grids/simgrid_zone_layer_mapping.lyr",
        well_attributes_file: str = None,
    ):
        super().__init__()
        self.theme = webviz_settings.theme
        self.colors = self.theme.plotly_theme["layout"]["colorway"]
        self.compdatfile = compdatfile
        self.ensembles = ensembles
        self.ens_paths = {
            ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
            for ens in ensembles
        }
        self.compdat = load_csv(ensemble_paths=self.ens_paths, csv_file=compdatfile)
        self.qc_compdat()
        self.layer_zone_mappings = json.load(
            read_zone_layer_mappings(
                ensemble_paths=self.ens_paths,
                zone_layer_mapping_file=zone_layer_mapping_file,
            )
        )

        self.well_attributes = self.read_well_attributes(well_attributes_file)

        # CACHE data at start-up
        for ens in self.ensembles:
            output = self.create_ensemble_dataset(ens)

        self.set_callbacks(app)

    def add_webvizstore(self):
        return [
            (
                load_csv,
                [{"ensemble_paths": self.ens_paths}, {"csv_file": self.compdatfile}],
            ),
            (
                read_zone_layer_mappings,
                [
                    {"ensemble_paths": self.ens_paths},
                    {"csv_file": self.zone_layer_mapping_file},
                ],
            ),
        ]

    def read_well_attributes(self, well_attributes_file):
        """
        Reads the well attributes json file and converts it into a dictionary \
        with eclipse_name as key
        """
        with open(well_attributes_file, "r") as handle:
            well_list = json.load(handle)

        output = {}
        for well_data in well_list:
            output[well_data["eclipse_name"]] = {
                key: item
                for key, item in well_data.items()
                if key not in ["eclipse_name", "rms_name"]
            }
        return output

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
                html.Div(id=self.uuid("well_completions_wrapper"),),
            ]
        )

    def set_callbacks(self, app):
        @app.callback(
            [
                Output(self.uuid("well_completions_wrapper"), "children"),
                Output(self.uuid("well_completions_wrapper"), "style"),
            ],
            [Input(self.uuid("ensemble_dropdown"), "value"),],
        )
        def _render_well_completions(ensemble_name):

            data = self.create_ensemble_dataset(ensemble_name)
            zones = len(data["stratigraphy"])
            return [
                webviz_subsurface_components.WellCompletions(
                    id="well_completions", data=data
                ),
                {"padding": "10px", "height": zones * 50},
            ]

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def create_ensemble_dataset(self, ensemble):
        """
        Creates the well completion data set for the WellCompletions component
        Returns a dictionary with given format
        """
        df = self.compdat[self.compdat.ENSEMBLE == ensemble].copy()
        ensemble_layer_zone_mapping = self.layer_zone_mappings[ensemble]
        df["ZONE"] = df.K1.astype(str).map(ensemble_layer_zone_mapping)

        time_steps = sorted(df.DATE.unique())
        realisations = np.asarray(sorted(df.REAL.unique()), dtype=np.int32)
        layers = np.sort(df.K1.unique())

        result = {}
        result["version"] = "1.0.0"
        result["stratigraphy"] = extract_stratigraphy(
            ensemble_layer_zone_mapping, self.colors
        )
        result["timeSteps"] = time_steps

        zone_names = [a["name"] for a in result["stratigraphy"]]
        result["wells"] = extract_wells(
            df, zone_names, time_steps, realisations, self.well_attributes
        )
        with open("/private/olind/webviz/result.json", "w") as f:
            json.dump(result, f)
            print("output exported")

        return result


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
            df_timestep = df[df.DATE == t]
            df_timestep_open = df_timestep[df_timestep["OP/SH"] == "OPEN"]

            # if minimum one of the compdats for the zone is OPEN then the zone is considered open
            event_value = 1 if len(df_timestep_open) > 0 else -1
            kh_value = df_timestep_open.KH.sum()

        events.append(event_value)
        kh.append(kh_value)
    return events, kh


def get_completion_events_and_kh(df, zone_names, time_steps, realisations):
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
        for zone_name in zone_names:
            zone_data = df[df.ZONE == zone_name]
            compl_events_real_zone, kh_real_zone = get_time_series(
                zone_data, time_steps
            )
            compl_events_real.append(compl_events_real_zone)
            kh_real.append(kh_real_zone)

        compl_events.append(compl_events_real)
        kh.append(kh_real)
    return compl_events, kh


def format_time_series(open_frac, shut_frac, kh_mean, kh_min, kh_max):
    """
    The functions takes in five lists with values per timestep
    * fractions of realisations open in this zone
    * fractions of realisations shut in this zone
    * kh mean over open realisations
    * kh min over open realisations
    * kh max over open realisations

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
    output = {"t": [], "open": [], "shut": [], "khMean": [], "khMin": [], "khMax": []}
    prev_open_val, prev_shut_val = (
        0,
        0,
    )

    for (i, (open_val, shut_val, kh_mean_val, kh_min_val, kh_max_val),) in enumerate(
        zip(open_frac, shut_frac, kh_mean, kh_min, kh_max)
    ):
        conditions = [
            open_val != prev_open_val,
            shut_val != prev_shut_val,
        ]
        if any(conditions):
            output["t"].append(i)
            output["open"].append(open_val)
            output["shut"].append(shut_val)
            output["khMean"].append(kh_mean_val)
            output["khMin"].append(kh_min_val)
            output["khMax"].append(kh_max_val)
        prev_open_val = open_val
        prev_shut_val = shut_val

    if len(output["t"]) == 0:
        return None
    return output


def extract_well(df, well, zone_names, time_steps, realisations, attributes):
    """
    Extract completion data for a single well
    """
    well_dict = {}
    well_dict["name"] = well

    compl_events, kh = get_completion_events_and_kh(
        df, zone_names, time_steps, realisations
    )

    # calculate fraction of open realizations
    open_count = np.maximum(np.asarray(compl_events), 0)  # remove -1
    open_count_reduced = open_count.sum(axis=0)  # sum over realizations
    open_frac = np.asarray(open_count_reduced, dtype=np.float64) / float(
        len(realisations)
    )

    # calculate fraction of shut realizations
    shut_count = (
        np.minimum(np.asarray(compl_events), 0) * -1
    )  # remove +1 and convert -1 to 1
    shut_count_reduced = shut_count.sum(axis=0)  # sum over realizations
    shut_frac = np.asarray(shut_count_reduced, dtype=np.float64) / float(
        len(realisations)
    )

    # calculate khMean, khMin and khMax
    kh_mean = np.asarray(kh).sum(axis=0) / float(len(realisations))
    kh_min = np.asarray(kh).min(axis=0)
    kh_max = np.asarray(kh).max(axis=0)

    result = {}
    for (
        zone_name,
        open_frac_zone,
        shut_frac_zone,
        kh_mean_zone,
        kh_min_zone,
        kh_max_zone,
    ) in zip(zone_names, open_frac, shut_frac, kh_mean, kh_min, kh_max):
        r = format_time_series(
            open_frac_zone, shut_frac_zone, kh_mean_zone, kh_min_zone, kh_max_zone
        )
        if r is not None:
            result[zone_name] = r
    well_dict["completions"] = result
    if attributes is not None:
        well_dict["attributes"] = attributes
    return well_dict


def extract_wells(df, zone_names, time_steps, realisations, well_attributes):
    """
    Generates the wells part of the input dictionary to the WellCompletions component
    """
    well_list = []
    for well_name, well_group in df.groupby("WELL"):
        attributes = None
        if well_name in well_attributes:
            attributes = well_attributes[well_name]
        well_list.append(
            extract_well(
                well_group, well_name, zone_names, time_steps, realisations, attributes
            )
        )
    return well_list


def extract_stratigraphy(layer_zone_mapping, colors):
    """
    Returns the stratigraphy part of the data set
    """
    color_iterator = itertools.cycle(colors)
    result = []
    zones = []
    for layer, zone in layer_zone_mapping.items():
        if zone not in zones:
            zones.append(zone)
            zdict = {}
            zdict["name"] = zone
            zdict["color"] = next(color_iterator)
            result.append(zdict)
    return result


@webvizstore
def read_zone_layer_mappings(ensemble_paths=None, zone_layer_mapping_file=None) -> io.BytesIO:
    """
    Reads the zone layer mappings for all ensembles using functionality \
    from the ecl2df library

    Should be rewritten to be more robust in case data is missing in r-0
    """
    if ensemble_paths == None or zone_layer_mapping_file == None:
        return {}
    output = {}
    eclfile = ecl2df.EclFiles("")
    for ens_name, ens_path in ensemble_paths.items():
        fn = f"{ens_path}/{zone_layer_mapping_file}".replace("*", "0")
        output[ens_name] = eclfile.get_zonemap(filename=fn)
    return io.BytesIO(
        json.dumps(output).encode()
    )