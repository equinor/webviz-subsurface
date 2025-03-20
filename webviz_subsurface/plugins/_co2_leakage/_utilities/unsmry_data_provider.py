from typing import Tuple, Union

import pandas as pd

from webviz_subsurface._providers import EnsembleTableProvider
from webviz_subsurface.plugins._co2_leakage._utilities.generic import (
    Co2MassScale,
    Co2VolumeScale,
    MenuOptions,
)

_PFLOTRAN_COLNAMES = ("DATE", "FGMDS", "FGMTR", "FGMGP")
_ECLIPSE_COLNAMES = ("DATE", "FWCD", "FGCDI", "FGCDM")


class UnsmryDataValidationError(Exception):
    pass


class UnsmryDataProvider:
    def __init__(self, provider: EnsembleTableProvider):
        UnsmryDataProvider._validate(provider)
        self._provider = provider
        (
            self._colname_date,
            self._colname_dissolved,
            self._colname_trapped,
            self._colname_mobile,
        ) = UnsmryDataProvider._column_subset_unsmry(provider)
        self._colname_total = "TOTAL"

    @property
    def menu_options(self) -> MenuOptions:
        return {
            "zones": [],
            "regions": [],
            "phases": ["total", "gas", "dissolved"],
            "plume_groups": [],
            "dates": [],
        }

    @property
    def colname_date(self) -> str:
        return self._colname_date

    @property
    def colname_dissolved(self) -> str:
        return self._colname_dissolved

    @property
    def colname_trapped(self) -> str:
        return self._colname_trapped

    @property
    def colname_mobile(self) -> str:
        return self._colname_mobile

    @property
    def colname_total(self) -> str:
        return self._colname_total

    def extract(self, scale: Union[Co2MassScale, Co2VolumeScale]) -> pd.DataFrame:
        columns = [
            self._colname_date,
            self._colname_dissolved,
            self._colname_trapped,
            self._colname_mobile,
        ]
        full = pd.concat(
            [
                self._provider.get_column_data(columns, [real]).assign(realization=real)
                for real in self._provider.realizations()
            ]
        )
        full[self._colname_total] = (
            full[self._colname_dissolved]
            + full[self._colname_trapped]
            + full[self.colname_mobile]
        )
        total_max = full[self._colname_total].max()
        for col in columns[1:] + [self._colname_total]:
            if scale == Co2MassScale.MTONS:
                full[col] = full[col] / 1e9
            elif scale == Co2MassScale.NORMALIZE:
                full[col] = full[col] / total_max
        return full

    @staticmethod
    def _column_subset_unsmry(
        provider: EnsembleTableProvider,
    ) -> Tuple[str, str, str, str]:
        existing = set(provider.column_names())
        # Try PFLOTRAN names
        if set(_PFLOTRAN_COLNAMES).issubset(existing):
            return _PFLOTRAN_COLNAMES
        # Try Eclipse names
        if set(_ECLIPSE_COLNAMES).issubset(existing):
            return _ECLIPSE_COLNAMES
        raise KeyError(
            f"Could not find suitable data columns among: {', '.join(existing)}"
        )

    @staticmethod
    def _validate(provider: EnsembleTableProvider) -> None:
        try:
            UnsmryDataProvider._column_subset_unsmry(provider)
        except KeyError as e:
            raise UnsmryDataValidationError from e
