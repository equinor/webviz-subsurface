import abc
from dataclasses import dataclass
from typing import List, Optional, Sequence

import pandas as pd


@dataclass(frozen=True)
class TableVectorMetadata:
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
    def vector_metadata(self, vector_name: str) -> Optional[TableVectorMetadata]:
        """Returns metadata for the specified vector. Returns None if no metadata
        exists or if any of the non-optional properties of `VectorMetadata` are missing.
        """
