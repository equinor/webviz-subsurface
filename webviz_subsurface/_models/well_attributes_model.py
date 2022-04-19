import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

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
        self._well_attributes = self._load_data()

    def __repr__(self) -> str:
        """This is necessary for webvizstore to work on objects"""
        return f"""
WellAttributesModel {self._ens_name} {self._ens_path} {self._well_attributes_file}
        """

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
    def _load_data(self) -> Optional[Dict[str, Any]]:
        ens = scratch_ensemble(self._ens_name, self._ens_path, filter_file="OK")
        df_files = ens.find_files(self._well_attributes_file)

        for _, row in df_files.iterrows():
            file_content = json.loads(Path(row["FULLPATH"]).read_text())
            return {
                well_data["alias"]["eclipse"]: well_data["attributes"]
                for well_data in file_content["wells"]
            }
        return None
