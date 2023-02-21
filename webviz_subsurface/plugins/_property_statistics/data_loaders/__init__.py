import pathlib

import pandas as pd
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore


@CACHE.memoize()
@webvizstore
def read_csv(csv_file: pathlib.Path) -> pd.DataFrame:
    return pd.read_csv(csv_file)
