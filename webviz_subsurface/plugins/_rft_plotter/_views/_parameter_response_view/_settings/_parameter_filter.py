from typing import List

from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from ......_components.parameter_filter import ParameterFilter
from ...._utils import RftPlotterDataModel


class ParameterFilterSettings(SettingsGroupABC):
    class Ids(StrEnum):
        PARAM_FILTER = "param-filter"

    def __init__(self, datamodel: RftPlotterDataModel) -> None:
        super().__init__("Parameter Filter")
        self._datamodel = datamodel
        self._params = datamodel.parameters if not datamodel.parameters is None else []
        self._parameter_df = datamodel.param_model.dataframe

    def layout(self) -> List[Component]:
        return ParameterFilter(
            uuid=self.register_component_unique_id(self.Ids.PARAM_FILTER),
            dframe=self._parameter_df[
                self._parameter_df["ENSEMBLE"].isin(
                    self._datamodel.param_model.mc_ensembles
                )
            ].copy(),
            reset_on_ensemble_update=True,
        ).layout
