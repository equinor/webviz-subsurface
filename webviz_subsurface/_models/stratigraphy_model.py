import glob
import io
import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

from webviz_config.webviz_store import webvizstore


class StratigraphyModel:
    """Facilitates loading of a json file with stratigraphy.

    The file needs to follow the format below. It is a tree structure, where each
    node has a name, an optional `color` parameter, and an optional `subzones`
    parameter which itself is a list of the same format.

    It is assumed that the file is the same for all realizations, so it will only
    read the first file it finds.


    ```json
    [
        {
            "name": "ZoneA",
            "color": "#FFFFFF",
            "subzones": [
                {
                    "name": "ZoneA.1"
                },
                {
                    "name": "ZoneA.2"
                }
            ]
        },
        {
            "name": "ZoneB",
            "color": "#FFF000",
            "subzones": [
                {
                    "name": "ZoneB.1",
                    "color": "#FFF111"
                },
                {
                    "name": "ZoneB.2",
                    "subzones: {"name": "ZoneB.2.2"}
                }
            ]
        },
    ]
    """

    def __init__(self, ens_name: str, ens_path: Path, stratigraphy_file: str):
        self._ens_name = ens_name
        self._ens_path = ens_path
        self._stratigraphy_file = stratigraphy_file
        self._data = json.load(self._load_data())

    @property
    def data(self) -> List[Dict[str, Any]]:
        """Returns the stratigraphy as a list of dictionaries"""
        return self._data

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
        """Descr"""

        for filename in glob.glob(f"{self._ens_path}/{self._stratigraphy_file}"):
            file_content = json.loads(Path(filename).read_text())
            logging.debug(f"Stratigrphy loaded from file: {filename}")
            return io.BytesIO(json.dumps(file_content).encode())
        return io.BytesIO(json.dumps({""}).encode())
