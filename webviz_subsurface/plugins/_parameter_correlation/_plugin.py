from typing import Callable, List, Tuple, Type

from dash.development.base_component import Component
from webviz_config import WebvizPluginABC, WebvizSettings

from ._error import error
from ._plugin_ids import PluginIds
from .views import ParameterPlot
from .views.parameter_plot._parameter_plot import get_parameters


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

        self.plot = ParameterPlot(self.ensembles, webviz_settings, drop_constants)

        self.add_view(
            self.plot,
            PluginIds.ParaCorrGroups.PARACORR,
            PluginIds.ParaCorrGroups.GROUPNAME,
        )

    @property
    def layout(self) -> Type[Component]:
        return error(self.error_message)

    @property
    def tour_steps(self) -> List[dict]:
        """Tour of the plugin"""
        return self.plot.tour_steps

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        return [
            (get_parameters, [{"ensemble_path": v} for v in self.ensembles.values()])
        ]
