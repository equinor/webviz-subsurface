import glob
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from ecl2df import EclFiles, common
from fmu.ensemble import ScratchEnsemble


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


def get_ecl_datafile(ensemble_path: str) -> Optional[str]:
    """Returns the first eclipse DATA file found in the ensemble_path.
    If no DATA file is found it returns None.
    """
    for filename in glob.glob(f"{ensemble_path}/eclipse/model/*.DATA"):
        return filename
    return None


def get_ecl_unit_system(ensemble_path: str) -> Optional[str]:
    """Returns the unit system of an eclipse deck. The options are \
    METRIC, FIELD, LAB and PVT-M.

    If none of these are found, the function returns METRIC

    If no eclipse DATA file is found in the ensemble path, it
    returns None
    """
    datafile = get_ecl_datafile(ensemble_path)
    if datafile is None:
        return None
    ecl_deck = EclFiles(datafile).get_ecldeck()
    for keyword in ecl_deck:
        if keyword.name in ["METRIC", "FIELD", "LAB", "PVT-M"]:
            return keyword.name
    return "METRIC"


def read_well_connection_status(
    ensemble_path: str, well_connection_status_file: str
) -> Optional[pd.DataFrame]:
    """Reads parquet file with well connection status data from the scratch disk.
    Merges together files from all realizations, does some fixing of the column
    data types, and returns it as a pandas dataframe.

    fmu-ensemble is used to find the file names on the scratch disk

    The well connection status data is extracted from the CPI data, which is 0 if the
    connection is SHUT and >0 if the connection is OPEN. This is independent of
    the status of the well.
    """
    ens = ScratchEnsemble("ens", ensemble_path)
    df_files = ens.find_files(well_connection_status_file)

    if df_files.empty:
        return None

    df = pd.DataFrame()
    for _, row in df_files.iterrows():
        df_real = pd.read_parquet(row.FULLPATH)
        df_real["REAL"] = row.REAL
        df = pd.concat([df, df_real])
    df.I = pd.to_numeric(df.I)
    df.J = pd.to_numeric(df.J)
    df["K1"] = pd.to_numeric(df.K)
    df = df.drop(["K"], axis=1)
    df.DATE = pd.to_datetime(df.DATE).dt.date
    return df
