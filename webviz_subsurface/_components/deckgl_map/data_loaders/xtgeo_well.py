from typing import List, Dict

from xtgeo import Well

# pylint: disable=too-few-public-methods
class XtgeoWellsJson:
    def __init__(self, wells: List[Well]):
        self._feature_collection = self._generate_feature_collection(wells)

    @property
    def feature_collection(self) -> Dict:
        return self._feature_collection

    def _generate_feature_collection(self, wells):
        features = []
        for well in wells:

            well.geometrics()
            features.append(self._generate_feature(well))
        return {"type": "FeatureCollection", "features": features}

    def _generate_feature(self, well):

        header = self._generate_header(well.xpos, well.ypos)
        dframe = well.dataframe[["X_UTME", "Y_UTMN", "Z_TVDSS"]]
        dframe["Z_TVDSS"] = dframe["Z_TVDSS"] * -1
        trajectory = self._generate_trajectory(values=dframe.values.tolist())

        properties = self._generate_properties(
            name=well.name, md_values=well.dataframe[well.mdlogname].values.tolist()
        )
        return {
            "type": "Feature",
            "geometry": {
                "type": "GeometryCollection",
                "geometries": [header, trajectory],
            },
            "properties": properties,
        }

    @staticmethod
    def _generate_header(xpos: float, ypos: float) -> dict:
        return {"type": "Point", "coordinates": [xpos, ypos]}

    @staticmethod
    def _generate_trajectory(values: List[float]) -> dict:
        return {"type": "LineString", "coordinates": values}

    @staticmethod
    def _generate_properties(name: str, md_values: list, colors: list = None) -> dict:
        return {
            "name": name,
            "color": colors if colors else [192, 192, 192, 192],
            "md": [md_values],
        }
