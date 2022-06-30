import pandas as pd
from webviz_config.webviz_plugin_subclasses import ViewABC

from .._pliginIds import PlugInIds
from ..view_elements import Graph


class PvtView(ViewABC):
    class Ids:
        # pylint disable too few arguments
        FORMATION_VOLUME_FACTOR = "formation-volume-factor"
        VISCOSITY = "viscosity"
        DENSITY = "density"
        GAS_OIL_RATIO = "gas-oil-ratio"

    def __init__(self, pvt_df: pd.DataFrame) -> None:
        super().__init__("Pvt View")

        self.pvt_df = pvt_df

        column = self.add_column()

        first_row = column.make_row()
        first_row.add_view_element(Graph(), PopulationIndicators.Ids.POPULATION)
        first_row.add_view_element(Graph(), PopulationIndicators.Ids.POPULATION_GROWTH)

        second_row = column.make_row()
        second_row.add_view_element(
            Graph(), PopulationIndicators.Ids.RURAL_VS_URBAN_POPULATION
        )
        second_row.add_view_element(
            Graph(), PopulationIndicators.Ids.RURAL_VS_URBAN_POPULATION_GROWTH
        )
