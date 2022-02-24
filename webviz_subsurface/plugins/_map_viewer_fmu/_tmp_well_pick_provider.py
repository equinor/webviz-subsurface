from typing import Optional, List, Dict
from enum import Enum

import pandas as pd
import geojson
from webviz_config.common_cache import CACHE


class WellPickTableColumns(str, Enum):
    X_UTME = "X_UTME"
    Y_UTMN = "Y_UTMN"
    Z_TVDSS = "Z_TVDSS"
    MD = "MD"
    WELL = "WELL"
    HORIZON = "HORIZON"


class WellPickProvider:
    def __init__(
        self,
        dframe: pd.DataFrame = None,
        map_surface_names_to_well_pick_names: Optional[Dict[str, str]] = None,
    ):
        self.dframe = dframe.copy()
        self.surface_name_mapper = (
            map_surface_names_to_well_pick_names
            if map_surface_names_to_well_pick_names
            else {}
        )
        self._validate()

    def _validate(self):
        for column in WellPickTableColumns:
            if column not in self.dframe.columns:
                raise KeyError(f"Well picks table is missing required column: {column}")

    def well_names(self):
        return list(self.dframe[WellPickTableColumns.WELL].unique())

    def get_geojson(self, well_names: List[str], surface_name: str):
        dframe = self.dframe.loc[
            (self.dframe[WellPickTableColumns.WELL].isin(well_names))
            & (
                self.dframe[WellPickTableColumns.HORIZON]
                == self.surface_name_mapper.get(surface_name, surface_name)
            )
        ]
        if dframe.empty:
            return {}
        validate_geometry = True
        feature_arr = []
        for _, row in dframe.iterrows():

            coords = [
                row[WellPickTableColumns.X_UTME],
                row[WellPickTableColumns.Y_UTMN],
            ]

            # coords = coords[0::20]
            point = geojson.Point(coordinates=coords, validate=validate_geometry)

            geocoll = geojson.GeometryCollection(geometries=[point])

            properties = {
                "name": row[WellPickTableColumns.WELL],
                "md": str(row[WellPickTableColumns.MD]),
                "tvd_msl": row[WellPickTableColumns.Z_TVDSS],
            }

            feature = geojson.Feature(
                id=row[WellPickTableColumns.WELL],
                geometry=geocoll,
                properties=properties,
            )
            feature_arr.append(feature)
        featurecoll = geojson.FeatureCollection(features=feature_arr)
        return featurecoll
