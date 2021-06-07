from typing import Optional, Dict, List, Tuple, Any
import json
import re
from pathlib import Path
import glob
import logging

import pandas as pd

from ecl2df import common


def remove_invalid_colors(zonelist: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Removes colors in the zonelist from the lyr file that is not 6 digit
    hexadecimal.
    """
    # pylint: disable=logging-fstring-interpolation
    for zonedict in zonelist:
        if "color" in zonedict and not re.match(
            "^#([A-Fa-f0-9]{6})", zonedict["color"]
        ):
            logging.getLogger(__name__).warning(
                f"""The zone color {zonedict["color"]} will be ignored. """
                "Only 6 digit hexadecimal colors are accepted in the well completions plugin."
            )
            zonedict.pop("color")
    return zonelist


def read_zone_layer_mapping(
    ensemble_path: str, zone_layer_mapping_file: str
) -> Tuple[Optional[Dict[int, str]], Optional[Dict[str, str]]]:
    """Searches for a zone layer mapping file (lyr format) on the scratch disk. \
    If one file is found it is parsed using functionality from the ecl2df \
    library.
    """
    for filename in glob.glob(f"{ensemble_path}/{zone_layer_mapping_file}"):
        zonelist = common.parse_lyrfile(filename=filename)
        layer_zone_mapping = common.convert_lyrlist_to_zonemap(zonelist)
        zonelist = remove_invalid_colors(zonelist)
        zone_color_mapping = {
            zonedict["name"]: zonedict["color"]
            for zonedict in zonelist
            if "color" in zonedict
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
    for filename in glob.glob(f"{ensemble_path}/eclipse/model/*.DATA"):
        with open(filename, "r") as handle:
            ecl_data_lines = handle.readlines()

        for unit_system in ["METRIC", "FIELD", "LAB", "PVT-M"]:
            if any(line.startswith(unit_system) for line in ecl_data_lines):
                return unit_system
        return None
    return None


def get_real_from_filename(filename: str) -> int:
    """Reads the realization number from the filepath. This will work
    if one of the parent folders for the file is on the
    """
    for item in filename.split("/"):
        if item.startswith("realization-"):
            return int(item.split("-")[1])
    raise ValueError(f"Realization number not found for {filename}")


def read_connection_status(
    ensemble_path: str, connection_status_file: str
) -> Optional[pd.DataFrame]:
    """Reads parquet file with connection status data from the scratch disk.
    Merges together files from all realizations, does some fixing of the column
    data types, and returns it as a pandas dataframe.

    The connection status data is extracted from the CPI data, which is 0 if the
    connection is SHUT and >0 if the connection is OPEN. This is independent of
    the status of the well.
    """
    files = glob.glob(f"{ensemble_path}/{connection_status_file}")
    if not files:
        return None

    df = pd.DataFrame()
    for filename in files:
        df_real = pd.read_parquet(filename)
        real = get_real_from_filename(filename)
        df_real["REAL"] = real
        df = pd.concat([df, df_real])
    df.I = pd.to_numeric(df.I)
    df.J = pd.to_numeric(df.J)
    df["K1"] = pd.to_numeric(df.K)
    df = df.drop(["K"], axis=1)
    df.DATE = pd.to_datetime(df.DATE).dt.date
    return df
