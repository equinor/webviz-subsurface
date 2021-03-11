from typing import List, Dict, Optional, Sequence
import datetime
import abc

import pandas as pd


# fmt: off

class EnsembleTimeSeries(abc.ABC):
    @abc.abstractmethod
    def vector_names(self) -> List[str]: ...

    @abc.abstractmethod
    def realizations(self) -> List[int]: ...

    @abc.abstractmethod
    def dates(self, realizations: Optional[Sequence[int]] = None) -> List[datetime.datetime]: ...

    @abc.abstractmethod
    def get_vectors_df(self, vector_names: Sequence[str], realizations: Optional[Sequence[int]] = None) -> pd.DataFrame: ...

    @abc.abstractmethod
    def get_vectors_for_date_df(self, date: datetime.datetime, vector_names: Sequence[str], realizations: Optional[Sequence[int]] = None) -> pd.DataFrame: ...

# fmt: on
