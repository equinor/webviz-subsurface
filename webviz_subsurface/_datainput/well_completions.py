from typing import Optional, Dict, List
import json
import re
from pathlib import Path
import glob

from ecl2df import common

def read_zone_layer_mapping(
    ensemble_path: str, zone_layer_mapping_file: str
) -> Optional[Dict[int, str]]:
    """Searches for a zone layer mapping file (lyr format) on the scratch disk. \
    If one file is found it is parsed using functionality from the ecl2df \
    library.
    """
    for filename in glob.glob(f"{ensemble_path}/{zone_layer_mapping_file}"):
        zonelist = common.parse_lyrfile(filename=filename)
        layer_zone_mapping = common.convert_lyrlist_to_zonemap(zonelist)
        zone_color_mapping = {
            zonedict["name"]:zonedict["color"] for zonedict in zonelist
            if "color" in zonedict and re.match("^#([A-Fa-f0-9]{6})", zonedict["color"])
        }
        return layer_zone_mapping, zone_color_mapping
    return None, None


def read_well_attributes(
    ensemble_path: str, well_attributes_file: str
) -> Optional[dict]:
    """Searches for a well attributes json file on the scratch disk. \
    if one file is found it is parsed and returned as a dictionary.

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
    for filename in glob.glob(f"{ensemble_path}/{well_attributes_file}"):
        file_content = json.loads(Path(filename).read_text())
        return {
            well_data["alias"]["eclipse"]: well_data["attributes"]
            for well_data in file_content["wells"]
        }
    return None

def read_stratigraphy(
    ensemble_path: str, stratigraphy_file: str
) -> Optional[List[Dict]]:
    """Searches for a stratigraphy json file on the scratch disk. \
    If a file is found the content is returned as a list of dicts.
    """
    for filename in glob.glob(f"{ensemble_path}/{stratigraphy_file}"):
        return json.loads(Path(filename).read_text())
    return None