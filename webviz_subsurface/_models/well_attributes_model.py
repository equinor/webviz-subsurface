import io
import json
from pathlib import Path
from typing import Callable, Dict, List, Tuple

import pandas as pd
from webviz_config.webviz_store import webvizstore

from webviz_subsurface._datainput.fmu_input import scratch_ensemble


class WellAttributesModel:
    """Facilitates loading of json file with well attributes.

    The file needs to follow the format below. The categorical attributes \
    are optional.
    {
        "version" : "0.1",
        "wells" : [
        {
            "alias" : {
                "eclipse" : "OP_1"
            },
            "attributes" : {
                "mlt_singlebranch" : "mlt",
                "structure" : "East",
                "welltype" : "producer"
            },
            "name" : "OP_1"
        },
        {
            "alias" : {
                "eclipse" : "GI_1"
            },
            "attributes" : {
                "mlt_singlebranch" : "singlebranch",
                "structure" : "West",
                "welltype" : "gas injector"
            },
            "name" : "GI_1"
        },
        ]
    }
    """

    def __init__(self, ens_name: str, ens_path: Path, well_attributes_file: str):
        self._ens_name = ens_name
        self._ens_path = ens_path
        self._well_attributes_file = well_attributes_file
        self._data: Dict[str, Dict[str, str]] = json.load(self._load_data())
        self._categories: List[str] = list(
            {name for categories in self._data.values() for name in categories}
        )

    def __repr__(self) -> str:
        """This is necessary for webvizstore to work on objects"""
        return f"""
WellAttributesModel {self._ens_name} {self._ens_path} {self._well_attributes_file}
        """

    @property
    def data(self) -> Dict[str, Dict[str, str]]:
        """Returns a dictionary with the well attributes data on the format:
        {
            "OP_1": {
                "mlt_singlebranch" : "mlt",
                "structure" : "East",
                "welltype" : "producer"
            },
            "OP_2 : {...}
        }

        where the key of the outer dictionary is the well eclipse alias.
        """
        return self._data

    @property
    def categories(self) -> List[str]:
        """List of all well attribute categories"""
        return self._categories

    @property
    def dataframe(self) -> pd.DataFrame:
        return pd.DataFrame.from_dict(self._data, orient="index")

    @property
    def webviz_store(self) -> Tuple[Callable, List[Dict]]:
        return (
            self._load_data,
            [
                {
                    "self": self,
                }
            ],
        )

    @webvizstore
    def _load_data(self) -> io.BytesIO:
        """This method reads the well attributes for an ensemble. It returns
        the data from the first file it finds so it is implicitly assumed that
        the file is equal for all realizations.
        """

        ens = scratch_ensemble(self._ens_name, self._ens_path, filter_file="OK")
        df_files = ens.find_files(self._well_attributes_file)

        for _, row in df_files.iterrows():
            file_content = json.loads(Path(row["FULLPATH"]).read_text())
            return io.BytesIO(
                json.dumps(
                    {
                        well_data["alias"]["eclipse"]: well_data["attributes"]
                        for well_data in file_content["wells"]
                    }
                ).encode()
            )
        return io.BytesIO(json.dumps({}).encode())
