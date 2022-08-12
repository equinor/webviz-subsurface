from typing import Callable, List, Tuple, Type

import pandas as pd
from dash.development.base_component import Component
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.common_cache import CACHE

from ._error import error
from ._plugin_ids import PluginIds
from .shared_settings import BothPlots, Horizontal, Options, Vertical
from .views import ParameterPlot
from .views._parameter_plot import get_parameters


class ParameterCorrelation(WebvizPluginABC):
    """Showing parameter correlations using a correlation matrix,
    and scatter plot for any given pair of parameters.

    ---

    * **`ensembles`:** Which ensembles in `shared_settings` to visualize.
    * **`drop_constants`:** Drop constant parameters.

    ---
    Parameter values are extracted automatically from the `parameters.txt` files in the individual
    realizations of your defined `ensembles`, using the `fmu-ensemble` library."""

    def __init__(
        self,
        webviz_settings: WebvizSettings,
        ensembles: list,
        drop_constants: bool = True,
    ) -> None:
        super().__init__(stretch=True)

        self.error_message = ""

        try:
            self.ensembles = {
                ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
                for ens in ensembles
            }
            self.plotly_theme = webviz_settings.theme.plotly_theme
        except TypeError:
            self.error_message = "WebvizSettings not iterable"
            self.ensembles = {"iter-0": "iter-0", "iter-3": "iter-3"}
        except AttributeError:
            self.error_message = "'Dash' object has no attribute 'theme'"

        self.drop_constants = drop_constants
        self.plot = ParameterPlot(
            self.ensembles, self.p_cols, webviz_settings, drop_constants
        )

        self.add_store(
            PluginIds.Stores.BothPlots.ENSEMBLE, WebvizPluginABC.StorageType.SESSION
        )
        self.add_shared_settings_group(
            BothPlots(self.ensembles), PluginIds.SharedSettings.BOTHPLOTS
        )

        self.add_store(
            PluginIds.Stores.Horizontal.ENSEMBLE, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.Horizontal.PARAMETER, WebvizPluginABC.StorageType.SESSION
        )
        self.add_shared_settings_group(
            Horizontal(self.ensembles, self.p_cols, self.plot),
            PluginIds.SharedSettings.HORIZONTAL,
        )

        self.add_store(
            PluginIds.Stores.Vertical.ENSEMBLE, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.Vertical.PARAMETER, WebvizPluginABC.StorageType.SESSION
        )
        self.add_shared_settings_group(
            Vertical(self.ensembles, self.p_cols, self.plot),
            PluginIds.SharedSettings.VERTICAL,
        )

        self.add_store(
            PluginIds.Stores.Options.COLOR_BY, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.Options.SHOW_SCATTER, WebvizPluginABC.StorageType.SESSION
        )
        self.add_shared_settings_group(
            Options(self.p_cols), PluginIds.SharedSettings.OPTIONS
        )

        self.add_store(
            PluginIds.Stores.Data.CLICK_DATA, WebvizPluginABC.StorageType.SESSION
        )

        self.add_view(
            self.plot,
            PluginIds.ParaCorrGroups.PARACORR,
            PluginIds.ParaCorrGroups.GROUPNAME,
        )

    @property
    def p_cols(self) -> list:
        dfs = [
            get_corr_data(ens, self.drop_constants) for ens in self.ensembles.values()
        ]
        return sorted(list(pd.concat(dfs, sort=True).columns))

    @property
    def layout(self) -> Type[Component]:
        return error(self.error_message)

    @property
    def tour_steps(self) -> List[dict]:
        """Tour of the plugin"""
        return [
            {
                "id": self.view(PluginIds.ParaCorrGroups.PARACORR)
                .layout_element(ParameterPlot.IDs.MAIN_COLUMN)
                .get_unique_id(),
                "content": "Displayting correlation between parameteres.",
            },
            {
                "id": self.view(PluginIds.ParaCorrGroups.PARACORR)
                .layout_element(ParameterPlot.IDs.MATRIX_ROW)
                .get_unique_id(),
                "content": "Matrix plot of the parameter correlation. You can "
                "click on the boxes to display the parameters in the scatterplot.",
            },
            {
                "id": self.view(PluginIds.ParaCorrGroups.PARACORR)
                .layout_element(ParameterPlot.IDs.SCATTER_ROW)
                .get_unique_id(),
                "content": "Scatterplot of the parameter correlation.",
            },
            {
                "id": self.shared_settings_group(
                    PluginIds.SharedSettings.BOTHPLOTS
                ).component_unique_id(BothPlots.IDs.ENSEMBLE),
                "content": "Choose which ensemble that is desired to show.",
            },
            {
                "id": self.shared_settings_group(
                    PluginIds.SharedSettings.HORIZONTAL
                ).component_unique_id(Horizontal.IDs.PARAMETER),
                "content": "Choose the parameter on the horizontal axis of the "
                "scatterplot.",
            },
            {
                "id": self.shared_settings_group(
                    PluginIds.SharedSettings.HORIZONTAL
                ).component_unique_id(Horizontal.IDs.ENSEMBLE),
                "content": "Choose the ensemble on the horizontal axis of the "
                "scatterplot.",
            },
            {
                "id": self.shared_settings_group(
                    PluginIds.SharedSettings.VERTICAL
                ).component_unique_id(Vertical.IDs.PARAMETER),
                "content": "Choose the parameter on the vertical axis of the "
                "scatterplot.",
            },
            {
                "id": self.shared_settings_group(
                    PluginIds.SharedSettings.VERTICAL
                ).component_unique_id(Vertical.IDs.ENSEMBLE),
                "content": "Choose the ensemble on the vertical axis of the "
                "scatterplot.",
            },
        ]

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        return [
            (get_parameters, [{"ensemble_path": v} for v in self.ensembles.values()])
        ]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_corr_data(ensemble_path: str, drop_constants: bool = True) -> pd.DataFrame:
    """
    if drop_constants:
    .dropna() removes undefined entries in correlation matrix after
    it is calculated. Correlations between constants yield nan values since
    they are undefined.
    Passing tuple or list to drop on multiple axes is deprecated since
    version 0.23.0. Therefor split in 2x .dropnan()
    """
    data = get_parameters(ensemble_path)

    # Necessary to drop constant before correlations due to
    # https://github.com/pandas-dev/pandas/issues/37448
    if drop_constants is True:
        for col in data.columns:
            if len(data[col].unique()) == 1:
                data = data.drop(col, axis=1)

    return (
        data.corr()
        if not drop_constants
        else data.corr()
        .dropna(axis="index", how="all")
        .dropna(axis="columns", how="all")
    )
