import logging
from functools import cached_property
from pathlib import Path
from typing import Any, Dict, List, Optional

from webviz_subsurface._utils.webvizstore_functions import read_csv
from webviz_subsurface.plugins._co2_leakage._utilities._misc import realization_paths
from webviz_subsurface.plugins._map_viewer_fmu._tmp_well_pick_provider import (
    WellPickProvider,
)

LOGGER = logging.getLogger(__name__)


class EnsembleWellPicks:
    def __init__(
        self,
        ens_path: str,
        well_picks_path: str,
        map_surface_names_to_well_pick_names: Optional[Dict[str, str]],
    ):
        self._absolute_well_pick_provider: Optional[WellPickProvider] = None
        self._per_real_well_pick_providers: Dict[int, WellPickProvider] = {}

        if Path(well_picks_path).is_absolute():
            self._absolute_well_pick_provider = _try_get_well_pick_provider(
                read_csv(well_picks_path),
                map_surface_names_to_well_pick_names,
            )
        else:
            realizations = realization_paths(ens_path)
            for r, r_path in realizations.items():
                try:
                    self._per_real_well_pick_providers[r] = WellPickProvider(
                        read_csv(r_path / well_picks_path),
                        map_surface_names_to_well_pick_names,
                    )
                except (FileNotFoundError, OSError) as e:
                    LOGGER.warning(
                        f"Failed to find well picks for realization {r} at {r_path}: {e}"
                    )

    @cached_property
    def well_names(self) -> List[str]:
        if self._absolute_well_pick_provider is not None:
            return self._absolute_well_pick_provider.well_names()

        return list(
            dict.fromkeys(
                w
                for v in self._per_real_well_pick_providers.values()
                for w in v.well_names()
            ).keys()
        )

    def geojson_layer(
        self, realization: int, selected_wells: List[str], formation: str
    ) -> Optional[Dict[str, Any]]:
        if self._absolute_well_pick_provider is not None:
            wpp = self._absolute_well_pick_provider
        elif realization in self._per_real_well_pick_providers:
            wpp = self._per_real_well_pick_providers[realization]
        else:
            return None

        well_data = dict(wpp.get_geojson(selected_wells, formation))
        if "features" in well_data:
            if len(well_data["features"]) == 0:
                wellstring = "well: " if len(selected_wells) == 1 else "wells: "
                wellstring += ", ".join(selected_wells)
                LOGGER.warning(
                    f"Combination of formation: {formation} and "
                    f"{wellstring} not found in well picks file."
                )
            for i in range(len(well_data["features"])):
                current_attribute = well_data["features"][i]["properties"]["attribute"]
                well_data["features"][i]["properties"]["attribute"] = (
                    " " + current_attribute
                )

        return {
            "@@type": "GeoJsonLayer",
            "name": "Well Picks",
            "id": "well-picks-layer",
            "data": well_data,
            "visible": True,
            "getText": "@@=properties.attribute",
            "getTextSize": 12,
            "getTextAnchor": "start",
            "pointType": "circle+text",
            "lineWidthMinPixels": 2,
            "pointRadiusMinPixels": 2,
            "pickable": True,
            "parameters": {"depthTest": False},
        }


def _try_get_well_pick_provider(
    p: Path, name_mapping: Optional[Dict[str, str]]
) -> Optional[WellPickProvider]:
    try:
        return WellPickProvider(read_csv(p), name_mapping)
    except OSError as e:
        LOGGER.warning(f"Failed to read well picks file '{p}': {e}")
        return None
