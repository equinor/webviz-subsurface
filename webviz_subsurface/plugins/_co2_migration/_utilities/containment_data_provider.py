import warnings
from typing import List, Optional, Sequence, Union

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

    def extract_dataframes(self, realizations: Sequence[int]) -> pd.DataFrame:
        df = self._provider.get_column_data(self._provider.column_names(), realizations)
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
        realization = provider.realizations()[0]
        df = provider.get_column_data(
            ["phase", "date", "zone", "region", "plume_group"]
        )
        ContainmentDataProvider._validate_dates_and_phases(provider, df, realization)
        reference_df = df.loc[df["REAL"] == realization, ["phase", "date"]]
        spatial_options = {
            column: ["all"]
            + [value for value in df[column].dropna().unique() if value != "all"]
            for column in ["zone", "region", "plume_group"]
        }
        zones = spatial_options["zone"]
        regions = spatial_options["region"]
        plume_groups = spatial_options["plume_group"]

        def plume_sort_key(name: Optional[str]) -> int:
            if name is None:
                return 999  # Not sure why/when this can happen, just a precaution
            if name == "undetermined":
                return 998
            return name.count("+")

        plume_groups = sorted(plume_groups, key=plume_sort_key)

        observed_phases = set(reference_df["phase"].dropna().unique())
        phases = [phase for phase in _PHASE_ORDER if phase in observed_phases]

        dates = reference_df["date"].unique()
        dates.sort()

        return {
            "zones": zones if len(zones) > 1 else [],
            "regions": regions if len(regions) > 1 else [],
            "phases": phases,
            "plume_groups": plume_groups if len(plume_groups) > 1 else [],
            "dates": dates,
        }

    @staticmethod
    def _validate_dates_and_phases(
        provider: EnsembleTableProvider,
        df: pd.DataFrame,
        reference_realization: int,
    ) -> None:
        for column in ["date", "phase"]:
            values_per_realization = df.groupby("REAL")[column].agg(
                lambda values: set(values.dropna())
            )
            expected = values_per_realization.loc[reference_realization]
            for realization, observed in values_per_realization.items():
                if observed != expected:
                    message = (
                        f"Inconsistent {column} sets for provider {provider}: "
                        f"realization {realization} differs from reference "
                        f"realization {reference_realization}. "
                        f"Missing: {sorted(expected - observed)}; "
                        f"extra: {sorted(observed - expected)}."
                    )
                    if column == "date":
                        warnings.warn(message, stacklevel=2)
                    else:
                        raise ContainmentDataValidationError(message)

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
