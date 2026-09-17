from typing import List, Optional, Union

import pandas as pd

from webviz_subsurface._providers import EnsembleTableProvider
from webviz_subsurface.plugins._co2_migration._utilities.generic import (
    Co2MassScale,
    Co2VolumeScale,
    MenuOptions,
)

_PHASE_ORDER = (
    "total",
    "gas",
    "moving_gas",
    "stationary_gas",
    "free_gas",
    "moving_free_gas",
    "stationary_free_gas",
    "trapped_gas",
    "dissolved_water",
    "dissolved_oil",
)


class ContainmentDataValidationError(Exception):
    pass


class ContainmentDataProvider:
    def __init__(self, table_provider: EnsembleTableProvider):
        ContainmentDataProvider._validate(table_provider)
        self._provider = table_provider
        self._menu_options = ContainmentDataProvider._get_menu_options(self._provider)

    @property
    def menu_options(self) -> MenuOptions:
        return self._menu_options

    @property
    def realizations(self) -> List[int]:
        return self._provider.realizations()

    def extract_dataframe(self, realization: int) -> pd.DataFrame:
        df = self._provider.get_column_data(
            self._provider.column_names(), [realization]
        )
        # Backward compatibility:
        df["containment"] = df["containment"].replace({"hazardous": "nogo"})
        return df

    def extract_condensed_dataframe(
        self,
        co2_scale: Union[Co2MassScale, Co2VolumeScale],
    ) -> pd.DataFrame:
        df = self._provider.get_column_data(self._provider.column_names())
        # Backward compatibility:
        df["containment"] = df["containment"].replace({"hazardous": "nogo"})

        df = df.loc[
            (df["zone"] == "all")
            & (df["region"] == "all")
            & (df["plume_group"] == "all")
        ]
        if co2_scale == Co2MassScale.MTONS:
            df.loc[:, "amount"] /= 1e9
        elif co2_scale == Co2MassScale.NORMALIZE:
            for r in self.realizations:
                mask = df["realization"] == r
                r_max = df.loc[mask, "amount"].max()
                df.loc[mask, "amount"] /= r_max
        return df

    @staticmethod
    def _get_menu_options(provider: EnsembleTableProvider) -> MenuOptions:
        col_names = provider.column_names()
        realization = provider.realizations()[0]
        # NBNB: Check that these are the same for all realizations????
        # NBNB: WARNING and empty for zones / regions, and Error if phases are different?
        df = provider.get_column_data(col_names, [realization])
        zones = ["all"]
        if "zone" in df:
            for zone in list(df["zone"]):
                if zone not in zones:
                    zones.append(zone)
        regions = ["all"]
        if "region" in df:
            for region in list(df["region"]):
                if region not in regions:
                    regions.append(region)
        plume_groups = ["all"]
        if "plume_group" in df:
            for plume_group in list(df["plume_group"]):
                if plume_group not in plume_groups and plume_group is not None:
                    plume_groups.append(plume_group)

        def plume_sort_key(name: Optional[str]) -> int:
            if name is None:
                return 999  # Not sure why/when this can happen, just a precaution
            if name == "undetermined":
                return 998
            return name.count("+")

        plume_groups = sorted(plume_groups, key=plume_sort_key)

        observed_phases = set(df["phase"].dropna().unique())
        phases = [phase for phase in _PHASE_ORDER if phase in observed_phases]

        dates = df["date"].unique()
        dates.sort()

        return {
            "zones": zones if len(zones) > 1 else [],
            "regions": regions if len(regions) > 1 else [],
            "phases": phases,
            "plume_groups": plume_groups if len(plume_groups) > 1 else [],
            "dates": dates,
        }

    @staticmethod
    def _validate(provider: EnsembleTableProvider) -> None:
        col_names = provider.column_names()
        required_columns = [
            "date",
            "amount",
            "phase",
            "containment",
            "zone",
            "region",
            "plume_group",
        ]
        missing_columns = [col for col in required_columns if col not in col_names]
        realization = provider.realizations()[0]
        if len(missing_columns) == 0:
            return
        raise ContainmentDataValidationError(
            f"EnsembleTableProvider validation error for provider {provider} in "
            f"realization {realization} (and possibly other csv-files).\n"
            f"  Expected columns: {', '.join(missing_columns)}\n"
            f"  Found columns: {', '.join(col_names)}\n"
            f"  (Missing columns: {', '.join(missing_columns)})"
            f"Provided files are possibly from an outdated version of ccs-scripts?"
        )
