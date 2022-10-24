import abc
from dataclasses import dataclass
from typing import List, Optional, Sequence

import pandas as pd


@dataclass(frozen=True)
class ColumnMetadata:
    unit: Optional[str]


class EnsembleTableProvider(abc.ABC):
    @abc.abstractmethod
    def column_names(self) -> List[str]:
        ...

    @abc.abstractmethod
    def realizations(self) -> List[int]:
        ...

    @abc.abstractmethod
    def get_column_data(
        self, column_names: Sequence[str], realizations: Optional[Sequence[int]] = None
    ) -> pd.DataFrame:
        ...

    @abc.abstractmethod
    def column_metadata(self, column_name: str) -> Optional[ColumnMetadata]:
        """Returns metadata for the specified column.

        Returns None if no metadata is found for the column.
        Returns a empty ColumnMetadata object if there is metadata, but it's
        not the columns specified in ColumnMetadata.
        """
