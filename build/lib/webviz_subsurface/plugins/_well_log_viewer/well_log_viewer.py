import json
from pathlib import Path
from typing import Callable, Dict, List, Tuple, Union

import webviz_core_components as wcc
from dash import Dash, html
from webviz_config import WebvizPluginABC
from webviz_subsurface_components import WellLogViewer as WellLogViewerComponent

from webviz_subsurface._models.well_set_model import WellSetModel
from webviz_subsurface._utils.webvizstore_functions import find_files, get_path

from ._validate_log_templates import load_and_validate_log_templates
from .controllers import well_controller
from .utils.default_color_tables import default_color_tables
from .utils.xtgeo_well_log_to_json import xtgeo_well_logs_to_json_format


class WellLogViewer(WebvizPluginABC):
    """Uses [videx-welllog](https://github.com/equinor/videx-wellog) to visualize well logs
    from files stored in RMS well format.

?> Currently tracks for visualizing discrete logs are not included. This will
be added in later releases.

---

* **`wellfolder`:** Path to a folder with well files stored in RMS well format.
* **`wellsuffix`:** File suffix of well files
* **`logtemplates`:** List of yaml based log template configurations. \
    See the data section for description of the format.
* **`mdlog`:** Name of the md log. If not specified, MD will be calculated.
* **`well_tvdmin`:** Truncate well data values above this depth.
* **`well_tvdmax`:** Truncate well data values below this depth.
* **`well_downsample_interval`:** Sampling interval used for coarsening a well trajectory
* **`colortables`:** Color tables on json format. See https://git.io/JDLyb \
    for an example file.
* **`initial_settings`:** Configuration for initializing the plugin with various \
    properties set. All properties are optional.
    See the data section for available properties.

---

?> The format and documentation of the log template configuration will be improved \
in later releases. A small configuration sample is provided below.

```yaml
name: All logs # Name of the log template
scale:
  primary: MD # Which reference track to visualize as default (MD/TVD)
  allowSecondary: False # Set to True to show both MD and TVD reference tracks.
tracks: # The list of log tracks
  - title: Porosity # Optional title of log track
    plots: # List of which logs to include in the track
      - name: PHIT # Upper case name of log
        type: area # Type of visualiation (area, line, linestep, dot)
        color: green # Color of log
      - name: PHIT_ORIG
        type: line
  - plots:
      - name: ZONE
        type: area
  - plots:
      - name: FACIES
        type: area
  - plots:
      - name: VSH
        type: area
  - plots:
      - name: SW
        type: dot
styles: # List of styles that can be added to tracks
```


Format of the `initial_settings` argument:
```yaml
        initial_settings:
            well: str # Name of well
            logtemplate: str # Name of log template
```
"""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        app: Dash,
        wellfolder: Path,
        logtemplates: List[Path],
        colortables: Path = None,
        wellsuffix: str = ".w",
        mdlog: str = None,
        well_tvdmin: Union[int, float] = None,
        well_tvdmax: Union[int, float] = None,
        well_downsample_interval: int = None,
        initial_settings: Dict = None,
    ):

        super().__init__()
        self._wellfolder = wellfolder
        self._wellsuffix = wellsuffix
        self._logtemplatefiles = logtemplates
        self._wellfiles: List = json.load(
            find_files(folder=self._wellfolder, suffix=self._wellsuffix)
        )
        self._log_templates = load_and_validate_log_templates(
            [get_path(fn) for fn in self._logtemplatefiles]
        )
        self._well_set_model = WellSetModel(
            self._wellfiles,
            mdlog=mdlog,
            tvdmin=well_tvdmin,
            tvdmax=well_tvdmax,
            downsample_interval=well_downsample_interval,
        )
        self.colortable_file = colortables
        if self.colortable_file:
            self.colortables = json.loads(get_path(self.colortable_file).read_text())
        else:
            self.colortables = default_color_tables()

        initial_settings = initial_settings if initial_settings else {}
        self.initial_well_name = initial_settings.get(
            "well_name", self._well_set_model.well_names[0]
        )
        self.initial_log_template = initial_settings.get(
            "logtemplate", list(self._log_templates.keys())[0]
        )
        self.set_callbacks(app)

    @property
    def layout(self) -> html.Div:
        return wcc.FlexBox(
            [
                wcc.Frame(
                    style={"height": "90vh", "flex": 1},
                    children=[
                        wcc.Dropdown(
                            label="Well",
                            id=self.uuid("well"),
                            options=[
                                {"label": name, "value": name}
                                for name in self._well_set_model.well_names
                            ],
                            value=self.initial_well_name,
                            clearable=False,
                        ),
                        wcc.Dropdown(
                            label="Log template",
                            id=self.uuid("template"),
                            options=[
                                {"label": name, "value": name}
                                for name in list(self._log_templates.keys())
                            ],
                            value=self.initial_log_template,
                            clearable=False,
                        ),
                    ],
                ),
                wcc.Frame(
                    style={"flex": 6, "height": "90vh"},
                    children=[
                        WellLogViewerComponent(
                            id=self.uuid("well-log-viewer"),
                            template=self._log_templates.get(self.initial_log_template),
                            welllog=xtgeo_well_logs_to_json_format(
                                well=self._well_set_model.get_well(
                                    self.initial_well_name
                                )
                            ),
                            colorTables=self.colortables,
                        )
                    ],
                ),
            ]
        )

    def set_callbacks(self, app: Dash) -> None:
        well_controller(
            app=app,
            well_set_model=self._well_set_model,
            log_templates=self._log_templates,
            get_uuid=self.uuid,
        )

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        store_functions = [
            (find_files, [{"folder": self._wellfolder, "suffix": self._wellsuffix}])
        ]

        store_functions.extend([(get_path, [{"path": fn}]) for fn in self._wellfiles])
        store_functions.extend(
            [(get_path, [{"path": fn}]) for fn in self._logtemplatefiles]
        )
        if self.colortable_file is not None:
            store_functions.append((get_path, [{"path": self.colortable_file}]))
        return store_functions
