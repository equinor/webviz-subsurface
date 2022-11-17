import itertools
import logging
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

import pandas as pd

from webviz_subsurface._utils.perf_timer import PerfTimer

from ...._models import StratigraphyModel, WellAttributesModel
from ...._providers import EnsembleTableProvider

LOGGER = logging.getLogger(__name__)


class WellCompletionDataModel:
    def __init__(
        self,
        ensemble_path: str,
        wellcompletion_provider: EnsembleTableProvider,
        stratigraphy_model: StratigraphyModel,
        well_attributes_model: WellAttributesModel,
        theme_colors: List[str],
    ) -> None:
        self._ensemble_path = ensemble_path
        self._theme_colors = theme_colors
        self._stratigraphy_model = stratigraphy_model
        self._stratigraphy = self._stratigraphy_model.data
        self._well_attributes_model = well_attributes_model
        self._well_attributes = self._well_attributes_model.data

        self._wellcompletion_df = wellcompletion_provider.get_column_data(
            column_names=wellcompletion_provider.column_names()
        )
        self._zones = self._wellcompletion_df["ZONE"].unique()
        self._realizations = sorted(self._wellcompletion_df["REAL"].unique())
        self._datemap = {
            dte: i
            for i, dte in enumerate(sorted(self._wellcompletion_df["DATE"].unique()))
        }
        self._wellcompletion_df["TIMESTEP"] = self._wellcompletion_df["DATE"].map(
            self._datemap
        )
        kh_metadata = wellcompletion_provider.column_metadata("KH")
        self._kh_unit = (
            kh_metadata.unit
            if kh_metadata is not None and kh_metadata.unit is not None
            else ""
        )
        self._kh_decimal_places = 2

    @property
    def webviz_store(self) -> List[Tuple[Callable, List[Dict]]]:
        return [
            self._well_attributes_model.webviz_store,
            self._stratigraphy_model.webviz_store,
        ]

    @property
    def realizations(self) -> List[int]:
        return self._realizations

    def create_ensemble_dataset(
        self, realization: Optional[int] = None
    ) -> Dict[str, Any]:
        """Creates the input data set for the WellCompletions component.

        Returns a dictionary on a given format specified here:
        https://github.com/equinor/webviz-subsurface-components/blob/master/react/src/lib/inputSchema/wellCompletions.json

        if realization is not None, the input dataframe is filtered on realizations.
        """
        timer = PerfTimer()

        df = self._wellcompletion_df
        if realization is not None:
            df = df[df["REAL"] == realization]

        dataset = {
            "version": "1.1.0",
            "units": {
                "kh": {"unit": self._kh_unit, "decimalPlaces": self._kh_decimal_places}
            },
            "stratigraphy": self._extract_stratigraphy(),
            "timeSteps": [
                pd.to_datetime(str(dte)).strftime("%Y-%m-%d")
                for dte in self._datemap.keys()
            ],
            "wells": self._extract_wells(df),
        }

        LOGGER.info(f"WellCompletion dataset created in {timer.elapsed_s():.2f}s")

        return dataset

    def _extract_wells(self, wellcompletion_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Generates the wells part of the input to the WellCompletions component."""
        well_list = []
        no_real = wellcompletion_df["REAL"].nunique()
        for well_name, well_group in wellcompletion_df.groupby("WELL"):
            well_data = _extract_well(well_group, well_name, no_real)
            well_data["attributes"] = (
                self._well_attributes[well_name]
                if well_name in self._well_attributes
                else {}
            )
            well_list.append(well_data)
        return well_list

    def _extract_stratigraphy(self) -> List[Dict[str, Any]]:
        """Returns the stratigraphy part of the input to the WellCompletions component."""
        color_iterator = itertools.cycle(self._theme_colors)

        # If no stratigraphy file is found then the stratigraphy is
        # created from the unique zones in the wellcompletiondata input.
        # They will then probably not come in the correct order.
        if self._stratigraphy is None:
            return [
                {
                    "name": zone,
                    "color": next(color_iterator),
                }
                for zone in self._zones
            ]

        # If stratigraphy is not None the following is done:
        stratigraphy, remaining_valid_zones = _filter_valid_nodes(
            self._stratigraphy, self._zones
        )

        if remaining_valid_zones:
            raise ValueError(
                "The following zones are defined in the well completion data, "
                f"but not in the stratigraphy: {remaining_valid_zones}"
            )

        return _add_colors_to_stratigraphy(stratigraphy, color_iterator)


def _add_colors_to_stratigraphy(
    stratigraphy: List[Dict[str, Any]],
    color_iterator: Iterator,
    zone_color_mapping: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """Add colors to the stratigraphy tree. The function will recursively parse the tree.

    There are tree sources of color:
    1. The color is given in the stratigraphy list, in which case nothing is done to the node
    2. The color is the optional the zone->color map
    3. If none of the above applies, the color will be taken from the theme color iterable for \
    the leaves. For other levels, a dummy color grey is used
    """
    for zonedict in stratigraphy:
        if "color" not in zonedict:
            if (
                zone_color_mapping is not None
                and zonedict["name"] in zone_color_mapping
            ):
                zonedict["color"] = zone_color_mapping[zonedict["name"]]
            elif "subzones" not in zonedict:
                zonedict["color"] = next(
                    color_iterator
                )  # theme colors only applied on leaves
            else:
                zonedict["color"] = "#808080"  # grey
        if "subzones" in zonedict:
            zonedict["subzones"] = _add_colors_to_stratigraphy(
                zonedict["subzones"],
                color_iterator,
                zone_color_mapping=zone_color_mapping,
            )
    return stratigraphy


def _extract_well(
    well_group: pd.DataFrame, well_name: str, no_real: int
) -> Dict[str, Any]:
    """Extract completion events and kh values for a single well"""
    well_dict: Dict[str, Any] = {}
    well_dict["name"] = well_name

    completions: Dict[str, Dict[str, List[Any]]] = {}
    for (zone, timestep), group_df in well_group.groupby(["ZONE", "TIMESTEP"]):
        data = group_df["OP/SH"].value_counts()
        if zone not in completions:
            completions[zone] = {
                "t": [],
                "open": [],
                "shut": [],
                "khMean": [],
                "khMin": [],
                "khMax": [],
            }
        zonedict = completions[zone]
        zonedict["t"].append(int(timestep))
        zonedict["open"].append(float(data["OPEN"] / no_real if "OPEN" in data else 0))
        zonedict["shut"].append(float(data["SHUT"] / no_real if "SHUT" in data else 0))
        zonedict["khMean"].append(round(float(group_df["KH"].mean()), 2))
        zonedict["khMin"].append(round(float(group_df["KH"].min()), 2))
        zonedict["khMax"].append(round(float(group_df["KH"].max()), 2))

    well_dict["completions"] = completions
    return well_dict


def _filter_valid_nodes(
    stratigraphy: List[Dict[str, Any]], valid_zone_names: List[str]
) -> Tuple[List, List]:
    """Returns the stratigraphy tree with only valid nodes.
    A node is considered valid if it self or one of it's subzones are in the
    valid zone names list (passed from the lyr file)

    The function recursively parses the tree to add valid nodes.
    """
    output = []
    remaining_valid_zones = valid_zone_names
    for zonedict in stratigraphy:
        if "subzones" in zonedict:
            zonedict["subzones"], remaining_valid_zones = _filter_valid_nodes(
                zonedict["subzones"], remaining_valid_zones
            )
        if zonedict["name"] in remaining_valid_zones:
            if "subzones" in zonedict and not zonedict["subzones"]:
                zonedict.pop("subzones")
            output.append(zonedict)
            remaining_valid_zones = [
                zone for zone in remaining_valid_zones if zone != zonedict["name"]
            ]  # remove zone name from valid zones if it is found in the stratigraphy
        elif "subzones" in zonedict and zonedict["subzones"]:
            output.append(zonedict)

    return output, remaining_valid_zones
