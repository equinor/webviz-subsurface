import glob
import io
import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

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
        self._data = list(json.load(self._load_data()))

    def __repr__(self) -> str:
        """This is necessary for webvizstore to work on objects"""
        return f"""
StratigraphyModel({self._ens_name!r}, {self._ens_path!r}, {self._stratigraphy_file!r})
        """

    @property
    def data(self) -> Optional[List[Dict[str, Any]]]:
        """Returns the stratigraphy if the list is not empty. If it is empty return None."""
        if self._data:
            return self._data
        return None

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
        """Reads the stratigraphy file for an ensemble. It returns the data from the first
        file it finds so it is assumed that the stratigraphy is equal for all realizations.

        If no file is found, it returns a empty list. Because of webvizstore it is not possible
        to return None.
        """

        for filename in glob.glob(f"{self._ens_path}/{self._stratigraphy_file}"):
            file_content = json.loads(Path(filename).read_text())
            logging.debug(f"Stratigraphy loaded from file: {filename}")
            return io.BytesIO(json.dumps(file_content).encode())
        return io.BytesIO(json.dumps("").encode())
