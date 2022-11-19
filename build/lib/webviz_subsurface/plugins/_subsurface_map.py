import json
import warnings
from pathlib import Path
from typing import Callable, List, Tuple
from uuid import uuid4

import pandas as pd
from dash import html
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore
from webviz_subsurface_components import Map

from .._datainput.fmu_input import scratch_ensemble


class SubsurfaceMap(WebvizPluginABC):
    """Visualizes reservoir grids in a map view, additionally it can
visualize the flow pattern in the simulation output using streamlines.
Input can be either a premade json object or data can be extracted from
a FMU ensemble.

---
**Two input options: Ensemble data or premade json file**

**json file**
* **`jsonfile`:** jsonfile with data, suitable for the \
corresponding [subsurface map component]\
(https://github.com/equinor/webviz-subsurface-components) \
 (absolute path or relative to config file).

**Ensemble data**
* **`ensemble`:** Which ensemble in `shared_settings` to visualize (**just one**).
* **`map_value`:** Which property to show in the map (e.g. `PERMX`).
* **`flow_value`:** Which property to use for the streamlines animation
  (e.g. `FLOWAT`).
* **`time_step`:** Which report or time step to use in the simulation output.

---

For ensemble data input, the key `FLORES` needs to be in the `RPTRST` keyword of the simulation
data deck for flow fields like `FLOWAT` and `FLOOIL` to be included in the data.

?> Using the ensemble method, the cell-by-cell mean values over all the grids in the ensemble are \
used, both for properties and flow fields. A consequence of this is that all the grids in the \
ensemble have to be equal (though the properties can vary), meaning that e.g. structural \
uncertainty unfortunately is not supported. Taking the cell-by-cell will also tend to \
give less property variations than you would see in a single realization. \
To look at a single realization you currently have to define a separate ensemble \
consisting of just a single realization.

!> Using the ensemble method, `UNRST` and `INIT` files are autodetected in the realizations under \
`eclipse/model`. You should therefore not have more than one of each of these files to make sure \
that you are reading the correct data.
"""

    def __init__(
        self,
        webviz_settings: WebvizSettings,
        jsonfile: Path = None,
        ensemble: str = None,
        map_value: str = None,
        flow_value: str = None,
        time_step: int = None,
    ):
        # TODO(Sigurd) What is the correct type(s) for time_step?

        super().__init__()

        self.jsonfile = jsonfile if jsonfile else None

        if jsonfile and ensemble:
            raise ValueError(
                'Incorrent arguments. Either provide a "jsonfile" or "ensemble", "map_value" '
                '"flow_value" and "time_step"'
            )
        if jsonfile:
            with open(get_path(jsonfile), "r") as filehandle:
                self.map_data = json.dumps(json.load(filehandle))
        elif ensemble and map_value and flow_value and time_step:
            self.map_value = map_value
            self.flow_value = flow_value
            self.time_step = time_step
            self.ensemble_path = webviz_settings.shared_settings["scratch_ensembles"][
                ensemble
            ]
            self.map_data = get_map_data(
                self.ensemble_path, self.map_value, self.flow_value, self.time_step
            )
        else:
            raise ValueError(
                'Incorrent arguments. Either provide a "jsonfile" or "ensemble", "map_value" '
                '"flow_value" and "time_step"'
            )
        self.map_id = f"map-{uuid4()}"

    @property
    def layout(self) -> html.Div:
        return html.Div([Map(id=self.map_id, data=self.map_data)])

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        return [
            (get_path, [{"path": Path(self.jsonfile)}])
            if self.jsonfile
            else (
                get_uncompressed_data,
                [
                    {
                        "ensemble_path": self.ensemble_path,
                        "map_value": self.map_value,
                        "flow_value": self.flow_value,
                        "time_step": self.time_step,
                    }
                ],
            )
        ]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_map_data(
    ensemble_path: str, map_value: str, flow_value: str, time_step: int
) -> str:
    """Returns map data in the format of a JSON string, suitable for the
    corresponding subsurface map component in
    https://github.com/equinor/webviz-subsurface-components
    """
    # pylint: disable=too-many-locals

    grid = get_uncompressed_data(ensemble_path, map_value, flow_value, time_step)

    indices_col = ["i", "j", "k"]
    x_col = ["x0", "x1", "x2", "x3"]
    y_col = ["y0", "y1", "y2", "y3"]
    flow_col = ["FLOWI+", "FLOWJ+"]

    resolution = 1000

    grid = grid[indices_col + x_col + y_col + ["value"] + flow_col]
    grid = grid[grid["value"] > 0]

    xmin, xmax = grid[x_col].values.min(), grid[x_col].values.max()
    ymin, ymax = grid[y_col].values.min(), grid[y_col].values.max()

    flowmin, flowmax = grid[flow_col].values.min(), grid[flow_col].values.max()

    valmin, valmax = grid["value"].min(), grid["value"].max()

    if (xmax - xmin) > (ymax - ymin):
        coord_scale = resolution / (xmax - xmin)
    else:
        coord_scale = resolution / (ymax - ymin)

    grid[x_col] = (grid[x_col] - xmin) * coord_scale
    grid[y_col] = (grid[y_col] - ymin) * coord_scale
    grid[x_col + y_col] = grid[x_col + y_col].astype(int)

    flow_scale = resolution / (flowmax - flowmin)
    grid[flow_col] = (grid[flow_col] - flowmin) * flow_scale
    grid[flow_col] = grid[flow_col].astype(int)

    val_scale = resolution / (valmax - valmin)
    grid["value"] = (grid["value"] - valmin) * val_scale
    grid["value"] = grid["value"].astype(int)

    grid[indices_col] = grid[indices_col].astype(int)

    data = {
        "values": grid.values.tolist(),
        "linearscales": {
            "coord": [float(coord_scale), float(xmin), float(ymin)],
            "value": [float(val_scale), float(valmin)],
            "flow": [float(flow_scale), float(flowmin)],
        },
    }

    return json.dumps(data, separators=(",", ":"))


@webvizstore
def get_uncompressed_data(
    ensemble_path: str, map_value: str, flow_value: str, time_step: int
) -> pd.DataFrame:

    ens = scratch_ensemble("", ensemble_path)

    properties = [map_value, f"{flow_value}I+", f"{flow_value}J+"]
    if "PERMX" not in properties:
        properties.append("PERMX")

    with warnings.catch_warnings():
        # Grid support outside initial scope of fmu-ensemble v2. Need to consider options
        warnings.filterwarnings("ignore", category=FutureWarning, module="fmu.ensemble")
        grid = ens.get_eclgrid(properties, report=time_step)

    grid = grid[grid["PERMX"] > 0]  # Remove inactive grid cells

    grid["value"] = grid[map_value]
    grid["FLOWI+"] = grid[f"{flow_value}I+"]
    grid["FLOWJ+"] = grid[f"{flow_value}J+"]

    # Webviz map component uses different corner point terminology than libecl
    for (new, old) in [
        ("x0", "x1"),
        ("x1", "x2"),
        ("x2", "x4"),
        ("y0", "y1"),
        ("y1", "y2"),
        ("y2", "y4"),
    ]:
        grid[new] = grid[old]

    return grid


@webvizstore
def get_path(path: Path) -> Path:
    return Path(path)
