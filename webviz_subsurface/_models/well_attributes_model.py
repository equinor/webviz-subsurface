import io
import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

import pandas as pd
from webviz_config.webviz_store import webvizstore

from webviz_subsurface._datainput.fmu_input import scratch_ensemble


class WellAttributesModel:
    """Facilitates loading of a json file with well attributes.

    The file needs to follow the format below. The categorical attributes \
    are completely flexible.
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
        self._data_raw: Dict[str, Any] = json.load(self._load_data())
        self._data: Dict[str, Dict[str, str]] = self._transform_data()
        self._categories: List[str] = list(
            {name for categories in self._data.values() for name in categories}
        )

    def __repr__(self) -> str:
        """This is necessary for webvizstore to work on objects"""
        return f"""
WellAttributesModel({self._ens_name!r}, {self._ens_path!r}, {self._well_attributes_file!r})
        """

    @property
    def data(self) -> Dict[str, Dict[str, str]]:
        """Returns the well attributes on the transformed format"""
        return self._data

    @property
    def categories(self) -> List[str]:
        """List of all well attribute categories"""
        return self._categories

    @property
    def file_name(self) -> str:
        """Returns the well attributes file name"""
        return self._well_attributes_file

    @property
    def dataframe(self) -> pd.DataFrame:
        """Returns the well attributes data as a dataframe with the well eclipse
        alias and categories as columns
        """
        return (
            pd.DataFrame.from_dict(self._data, orient="index")
            .rename_axis("WELL")
            .reset_index()
        )

    @property
    def dataframe_melted(self) -> pd.DataFrame:
        """Returns the well attributes data as melted dataframe, that means with
        only three columns: WELL, CATEGORY and VALUE
        """
        return self.dataframe.melt(
            id_vars=["WELL"], value_vars=self._categories
        ).rename({"variable": "CATEGORY", "value": "VALUE"}, axis=1)

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
        the files are equal for all realizations.
        """
        ens = scratch_ensemble(self._ens_name, self._ens_path, filter_file="OK")
        df_files = ens.find_files(self._well_attributes_file)

        for _, row in df_files.iterrows():
            file_content = json.loads(Path(row["FULLPATH"]).read_text())
            logging.debug(f"Well attributes loaded from file: {row['FULLPATH']}")
            return io.BytesIO(json.dumps(file_content).encode())
        return io.BytesIO(json.dumps({}).encode())

    def _transform_data(self) -> Dict[str, Dict[str, str]]:
        """Transforms the well attributes format to a simpler form
        where the key of the outer dictionary is the well eclipse alias:
        {
            "OP_1": {
                "mlt_singlebranch" : "mlt",
                "structure" : "East",
                "welltype" : "producer"
            },
            "OP_2 : {...}
        }
        """
        if self._data_raw["version"] != "0.1":
            raise NotImplementedError(
                f"Version {self._data_raw['version']} of the well attributes file "
                "is not implemented."
            )
        return {
            well_data["alias"]["eclipse"]: well_data["attributes"]
            for well_data in self._data_raw["wells"]
        }
