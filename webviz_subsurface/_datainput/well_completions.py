import json
from pathlib import Path
import glob
import ecl2df


def read_zone_layer_mapping(ensemble_path: str, zone_layer_mapping_file: str):
    """
    Searches for a zone layer mapping file (lyr format) on the scratch disk. \
    If one file is found it is parsed using functionality from the ecl2df \
    library.
    """
    eclfile = ecl2df.EclFiles("")
    for filename in glob.glob(f"{ensemble_path}/{zone_layer_mapping_file}"):
        if Path(filename).exists():
            return eclfile.get_zonemap(filename=filename)
    return None


def read_well_attributes(ensemble_path: str, well_attributes_file: str):
    """
    Searches for a well attributes json file on the scratch disk. \
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

    def read_well_attributes_file(filepath):
        file_content = json.loads(filepath.read_text())
        well_list = file_content["wells"]
        output = {}
        for well_data in well_list:
            eclipse_name = well_data["alias"]["eclipse"]
            output[eclipse_name] = well_data["attributes"]
        return output

    for filename in glob.glob(f"{ensemble_path}/{well_attributes_file}"):
        filepath = Path(filename)
        if filepath.exists():
            return read_well_attributes_file(filepath)
    return None
