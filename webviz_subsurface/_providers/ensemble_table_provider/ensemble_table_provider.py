import abc
from typing import List, Optional, Sequence

import pandas as pd


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
