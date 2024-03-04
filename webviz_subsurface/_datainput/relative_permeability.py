from pathlib import Path
from typing import Any, Optional, Union

import pandas as pd
from webviz_config.webviz_store import webvizstore

from .fmu_input import load_ensemble_set

try:
    import res2df
except ImportError:
    pass

try:
    from pyscal import PyscalFactory
except ImportError:
    pass


@webvizstore
def load_satfunc(
    ensemble_paths: dict,
    ensemble_set_name: str = "EnsembleSet",
) -> pd.DataFrame:
    def res2df_satfunc(kwargs: Any) -> pd.DataFrame:
        return res2df.satfunc.df(kwargs["realization"].get_eclfiles())

    return load_ensemble_set(ensemble_paths, ensemble_set_name).apply(res2df_satfunc)


@webvizstore
def load_scal_recommendation(
    scalfile: Path, sheet_name: Optional[Union[str, int, list]] = None
) -> pd.DataFrame:
    return (
        PyscalFactory.create_scal_recommendation_list(
            PyscalFactory.load_relperm_df(str(scalfile), sheet_name)
        )
        .df()
        .replace(
            {
                "CASE": {
                    "(?i)low": "pess",
                    r"(?i)^pes.*": "pess",
                    "(?i)base": "base",
                    "(?i)high": "opt",
                    r"(?i)^opt.*": "opt",
                }
            },
            regex=True,
        )
    )
