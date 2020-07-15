import dash
import dash_table
import pandas as pd
import numpy as np
from pathlib import Path

class FilterTable:
    def __init__(
            self,
            target_points = None,
            well_points = None,
    ):
        self.target_points = target_points
        self.well_points = well_points

    def get_targetpoints_datatable(self):
        df = pd.read_csv(self.target_points)
        return df.round(2)

    def get_wellpoints_datatable(self):
        df = pd.read_csv(self.well_points)
        return df.round(2)

    def update_wellpoints_datatable(self,column_list):
        df = pd.read_csv(self.well_points)
        sorted_list = []
        for colm in df.keys().values:
            for col in column_list:
                if colm == col:
                    sorted_list.append(col)
        return df[sorted_list].round(2)