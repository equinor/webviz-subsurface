from typing import Optional, Dict, List, Tuple
import json
import re
from pathlib import Path
import glob

from ecl2df import common


def read_zone_layer_mapping(
    ensemble_path: str, zone_layer_mapping_file: str
) -> Tuple[Optional[Dict[int, str]], Optional[Dict[str, str]]]:
    """Searches for a zone layer mapping file (lyr format) on the scratch disk. \
    If one file is found it is parsed using functionality from the ecl2df \
    library.
    """
    # pylint: disable=no-member
    for filename in glob.glob(f"{ensemble_path}/{zone_layer_mapping_file}"):
        zonelist = common.parse_lyrfile(filename=filename)
        layer_zone_mapping = common.convert_lyrlist_to_zonemap(zonelist)
        zone_color_mapping = {
            zonedict["name"]: zonedict["color"]
            for zonedict in zonelist
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


def get_ecl_unit_system(ensemble_path: str) -> Optional[str]:
    """Returns the unit system of an eclipse deck. The options are \
    METRIC, FIELD, LAB and PVT-M.

    If none of these are found, the function returns None, even though \
    the default unit system is METRIC. This is because the unit system \
    keyword could be in an include file.
    """

    def ecldata_has_unit_system(unit_system: str, lines: list) -> bool:
        for line in lines:
            if line.startswith(unit_system):
                return True
        return False

    unit_systems = ["METRIC", "FIELD", "LAB", "PVT-M"]
    for filename in glob.glob(f"{ensemble_path}/eclipse/model/*.DATA"):
        with open(filename, "r") as handle:
            ecl_data_lines = handle.readlines()

        for unit_system in unit_systems:
            if ecldata_has_unit_system(unit_system, ecl_data_lines):
                return unit_system
        return None
    return None
