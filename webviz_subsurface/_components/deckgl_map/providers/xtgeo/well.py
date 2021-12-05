from dataclasses import asdict, dataclass, field
from enum import Enum
from re import X
from typing import Dict, List

from geojson import (
    Feature,
    FeatureCollection,
    GeoJSON,
    GeometryCollection,
    LineString,
    Point,
    dumps,
)
from xtgeo import Well


class XtgeoCoords(str, Enum):
    X = "X_UTME"
    Y = "Y_UTMN"
    Z = "Z_TVDSS"


@dataclass
class WellProperties:
    name: str
    md: List[float]
    color: List[int] = field(default_factory=lambda: [192, 192, 192, 192])


# pylint: disable=too-few-public-methods
class WellToJson(FeatureCollection):
    def __init__(self, wells: List[Well]) -> None:
        self.type = "FeatureCollection"
        self.features = []
        for well in wells:
            if well.mdlogname is None:
                well.geometrics()
            self.features.append(self._generate_feature(well))

    def _generate_feature(self, well: Well) -> Feature:

        header = self._generate_header(well.xpos, well.ypos)
        dframe = well.dataframe[[coord for coord in XtgeoCoords]]

        dframe[XtgeoCoords.Z] *= -1
        trajectory = self._generate_trajectory(values=dframe.values.tolist())

        return Feature(
            geometry=GeometryCollection(
                geometries=[header, trajectory],
            ),
            properties=asdict(
                WellProperties(
                    name=well.name, md=well.dataframe[well.mdlogname].values.tolist()
                )
            ),
        )

    @staticmethod
    def _generate_header(xpos: float, ypos: float) -> Point:
        return Point(coordinates=[xpos, ypos])

    @staticmethod
    def _generate_trajectory(values: List[float]) -> LineString:
        return LineString(coordinates=values)
