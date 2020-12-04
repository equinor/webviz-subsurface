from pathlib import Path
from typing import List

import pandas as pd


class FilterTable:
    """Uses paths to csv files to render dataframes
    and to update them.
    * `target_points`: File path to targetpoints.csv
    * `well_points`: File path to wellpoints.csv
    """

    def __init__(
        self,
        target_points: Path = None,
        well_points: Path = None,
    ):
        self.target_points = target_points
        self.well_points = well_points

    def get_targetpoints_df(self) -> pd.DataFrame:
        df = pd.read_csv(self.target_points)
        return df.round(2)

    def get_wellpoints_df(self) -> pd.DataFrame:
        df = pd.read_csv(self.well_points)
        return df.round(2)

    def update_wellpoints_df(self, column_list: List[str]) -> pd.DataFrame:
        df = pd.read_csv(self.well_points)
        sorted_list = []
        for colm in df.keys().values:
            for col in column_list:
                if colm == col:
                    sorted_list.append(col)
        return df[sorted_list].round(2)
