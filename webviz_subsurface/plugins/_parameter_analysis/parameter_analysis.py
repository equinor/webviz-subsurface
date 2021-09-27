import pathlib
from typing import Optional

from dash import dcc
from webviz_config import WebvizPluginABC, WebvizSettings

from webviz_subsurface._components.parameter_filter import ParameterFilter
from webviz_subsurface._models import (
    EnsembleSetModel,
    caching_ensemble_set_model_factory,
)

from .controllers import parameter_qc_controller, parameter_response_controller
from .data_loaders import read_csv
from .models import ParametersModel, SimulationTimeSeriesModel
from .views import main_view


class ParameterAnalysis(WebvizPluginABC):
    """This plugin visualizes parameter distributions and statistics. /
    for FMU ensembles, and can be used to investigate parameter correlations /
    on reservoir simulation time series data.

---

**Input data can be provided in two ways: Aggregated or read from ensembles stored on scratch.**

**Using aggregated data**
* **`csvfile_parameters`:** Aggregated `csv` file with `REAL`, `ENSEMBLE` and parameter columns. \
    (absolute path or relative to config file).
* **`csvfile_smry`:** (Optional) Aggregated `csv` file for volumes with `REAL`, `ENSEMBLE`, `DATE` \
    and vector columns (absolute path or relative to config file).

**Using raw ensemble data stored in realization folders**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`column_keys`:** List of vectors to extract. If not given, all vectors \
    from the simulations will be extracted. Wild card asterisk `*` can be used.
* **`time_index`:** Time separation between extracted values. Can be e.g. `monthly` (default) or \
    `yearly`.

**Common settings for all input options**
* **`drop_constants`:** Bool used to determine if constant parameters should be dropped. \
    Default is True.

---

!> For smry data it is **strongly recommended** to keep the data frequency to a regular frequency \
(like `monthly` or `yearly`). This applies to both csv input and when reading from `UNSMRY` \
(controlled by the `sampling` key). This is because the statistics and fancharts are calculated \
per DATE over all realizations in an ensemble, and the available dates should therefore not \
differ between individual realizations of an ensemble.

?> Vectors that are identified as historical vectors (e.g. FOPTH is the history of FOPT) will \
be plotted together with their non-historical counterparts as reference lines.

**Using simulation time series data directly from `.UNSMRY` files**

!> Parameter values are extracted automatically from the `parameters.txt` files in the individual
realizations if you have defined `ensembles`, using the `fmu-ensemble` library.

!> The `UNSMRY` files are auto-detected by `fmu-ensemble` in the `eclipse/model` folder of the \
individual realizations. You should therefore not have more than one `UNSMRY` file in this \
folder, to avoid risk of not extracting the right data.

**Using aggregated data**

?> Aggregated data may speed up the build of the app, as processing of `UNSMRY` files can be \
slow for large models.

"""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        app,
        webviz_settings: WebvizSettings,
        ensembles: Optional[list] = None,
        csvfile_parameters: pathlib.Path = None,
        csvfile_smry: pathlib.Path = None,
        time_index: str = "monthly",
        column_keys: Optional[list] = None,
        drop_constants: bool = True,
    ):
        super().__init__()

        self.theme = webviz_settings.theme
        self.time_index = time_index
        self.column_keys = column_keys
        self.ensembles = ensembles
        self.csvfile_parameters = csvfile_parameters
        self.csvfile_smry = csvfile_smry

        if ensembles is not None:
            self.emodel: EnsembleSetModel = (
                caching_ensemble_set_model_factory.get_or_create_model(
                    ensemble_paths={
                        ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
                        for ens in ensembles
                    },
                    time_index=self.time_index,
                    column_keys=self.column_keys,
                )
            )
            self.pmodel = ParametersModel(
                dataframe=self.emodel.load_parameters(),
                theme=self.theme,
                drop_constants=drop_constants,
            )
            self.vmodel = SimulationTimeSeriesModel(
                dataframe=self.emodel.get_or_load_smry_cached()
            )

        elif self.csvfile_parameters is None:
            raise ValueError("Either ensembles or csvfile_parameters must be specified")
        else:
            self.pmodel = ParametersModel(
                dataframe=read_csv(csvfile_parameters),
                theme=self.theme,
                drop_constants=drop_constants,
            )
            if self.csvfile_smry is not None:
                self.vmodel = SimulationTimeSeriesModel(
                    dataframe=read_csv(csvfile_smry)
                )
            else:
                self.vmodel = None

        self._parameter_filter = ParameterFilter(
            app, self.uuid("parameter-filter"), self.pmodel.dataframe
        )

        self.set_callbacks(app)

    @property
    def layout(self) -> dcc.Tabs:
        return main_view(
            get_uuid=self.uuid,
            vectormodel=self.vmodel,
            parametermodel=self.pmodel,
            parameterfilter_layout=self._parameter_filter.layout,
            theme=self.theme,
        )

    def set_callbacks(self, app) -> None:
        parameter_qc_controller(app=app, get_uuid=self.uuid, parametermodel=self.pmodel)
        if self.vmodel is not None:
            parameter_response_controller(
                app=app,
                get_uuid=self.uuid,
                parametermodel=self.pmodel,
                vectormodel=self.vmodel,
            )

    def add_webvizstore(self):
        store = []
        if self.ensembles is not None:
            store.extend(self.emodel.webvizstore)
        else:
            store.append(
                (
                    read_csv,
                    [
                        {"csv_file": self.csvfile_parameters},
                    ],
                )
            )
            if self.csvfile_smry is not None:
                store.append(
                    (
                        read_csv,
                        [
                            {"csv_file": self.csvfile_smry},
                        ],
                    )
                )

        return store
