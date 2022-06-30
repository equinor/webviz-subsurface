
import pandas as pd
from webviz_config.webviz_plugin_subclasses import ViewABC

class PvtView(ViewABC):
    class Ids:
        #pylint disable too few arguments
        NAME =""
    def __init__(self, pvt_df: pd.DataFrame) -> None:
        super().__init__("Pvt View")

        self.pvt_df = pvt_df

        






        