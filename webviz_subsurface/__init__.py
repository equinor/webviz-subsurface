import glob
import pathlib
from typing import Dict, Optional

import jsonschema
import webviz_config
import yaml
from pkg_resources import DistributionNotFound, get_distribution

from webviz_subsurface._utils.user_defined_vector_definitions import (
    USER_DEFINED_VECTOR_DEFINITIONS_JSON_SCHEMA,
)
from webviz_subsurface._utils.vector_calculator import (
    PREDEFINED_EXPRESSIONS_JSON_SCHEMA,
    ConfigExpressionData,
)

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    pass


@webviz_config.SHARED_SETTINGS_SUBSCRIPTIONS.subscribe("scratch_ensembles")
def subscribe_scratch_ensembles(
    scratch_ensembles: dict, config_folder: pathlib.Path, portable: bool
) -> dict:
    if scratch_ensembles is not None:
        for ensemble_name, ensemble_path in scratch_ensembles.items():
            if not pathlib.Path(ensemble_path).is_absolute():
                scratch_ensembles[ensemble_name] = str(config_folder / ensemble_path)

            if not portable and not glob.glob(
                str(pathlib.Path(scratch_ensembles[ensemble_name]) / "OK")
            ):
                if not glob.glob(scratch_ensembles[ensemble_name]):
                    raise ValueError(
                        f"Ensemble {ensemble_name} is said to be located at {ensemble_path},"
                        " but that wildcard path does not give any matches."
                    )
                raise ValueError(
                    f"No realizations with a valid ERT 'OK' file found for ensemble "
                    f"{ensemble_name} located at {ensemble_path}. This can occur if an ERT job "
                    "has failed in all realizations, or none of the realizations have finished yet."
                )

    return scratch_ensembles


@webviz_config.SHARED_SETTINGS_SUBSCRIPTIONS.subscribe("predefined_expressions")
def subscribe_predefined_expressions(
    predefined_expressions: Optional[Dict[str, str]],
    config_folder: pathlib.Path,
    portable: bool,
) -> Dict[str, pathlib.Path]:

    output: Dict[str, pathlib.Path] = {}

    if predefined_expressions is None:
        return output

    for key, path in predefined_expressions.items():

        if not pathlib.Path(path).is_absolute():
            output[key] = config_folder / path

        if not portable:
            predefined_expressions_data: Dict[
                str, ConfigExpressionData
            ] = yaml.safe_load(output[key].read_text())

            try:
                jsonschema.validate(
                    instance=predefined_expressions_data,
                    schema=PREDEFINED_EXPRESSIONS_JSON_SCHEMA,
                )
            except jsonschema.exceptions.ValidationError as err:
                raise ValueError from err

    return output


@webviz_config.SHARED_SETTINGS_SUBSCRIPTIONS.subscribe(
    "user_defined_vector_definitions"
)
def subscribe_user_defined_vector_definitions(
    user_defined_vector_definitions: Optional[Dict[str, str]],
    config_folder: pathlib.Path,
    portable: bool,
) -> Dict[str, pathlib.Path]:

    output: Dict[str, pathlib.Path] = {}

    if user_defined_vector_definitions is None:
        return output

    for key, path in user_defined_vector_definitions.items():

        if not pathlib.Path(path).is_absolute():
            output[key] = config_folder / path

        if not portable:
            vector_definitions: Dict[str, str] = yaml.safe_load(output[key].read_text())

            try:
                jsonschema.validate(
                    instance=vector_definitions,
                    schema=USER_DEFINED_VECTOR_DEFINITIONS_JSON_SCHEMA,
                )
            except jsonschema.exceptions.ValidationError as err:
                raise ValueError from err

    return output
