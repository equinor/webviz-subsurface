from typing import Any, Callable, Dict, List, Optional, Tuple

import xtgeo
from dash import Dash, Input, Output

from webviz_subsurface._models.well_set_model import WellSetModel


def well_controller(
    app: Dash,
    well_set_model: WellSetModel,
    log_templates: Dict,
    get_uuid: Callable,
) -> None:
    @app.callback(
        Output(get_uuid("well-log-viewer"), "welllog"),
        Output(get_uuid("well-log-viewer"), "template"),
        Input(get_uuid("well"), "value"),
        Input(get_uuid("template"), "value"),
    )
    def _update_log_data(well_name: str, template: str) -> Tuple[Any, Any]:
        well = well_set_model.get_well(well_name)
        return xtgeo_well_logs_to_json_format(well), log_templates.get(template)


def xtgeo_well_logs_to_json_format(well: xtgeo.Well) -> List[Dict]:

    header = generate_header(well_name=well.name)
    curves = []

    # Calculate well geometrics if MD log is not provided
    if well.mdlogname is None:
        well.geometrics()

    # Add MD and TVD curves
    curves.append(generate_curve(log_name="MD", description="Measured depth"))
    curves.append(
        generate_curve(log_name="TVD", description="True vertical depth (SS)")
    )
    # Add additonal logs, skipping geometrical logs if calculated
    lognames = [
        logname
        for logname in well.lognames
        if logname not in ["Q_MDEPTH", "Q_AZI", "Q_INCL", "R_HLEN"]
    ]
    for logname in lognames:
        curves.append(generate_curve(log_name=logname.upper()))

    # Filter dataframe to only include relevant logs
    curve_names = [well.mdlogname, "Z_TVDSS"] + lognames
    dframe = well.dataframe[curve_names]
    dframe = dframe.reindex(curve_names, axis=1)

    return [{"header": header, "curves": curves, "data": dframe.values.tolist()}]


def generate_header(well_name: str, logrun_name: str = "log") -> Dict[str, Any]:
    return {
        "name": logrun_name,
        "well": well_name,
        "wellbore": None,
        "field": None,
        "country": None,
        "date": None,
        "operator": None,
        "serviceCompany": None,
        "runNumber": None,
        "elevation": None,
        "source": None,
        "startIndex": None,
        "endIndex": None,
        "step": None,
        "dataUri": None,
    }


def generate_curve(
    log_name: str, description: Optional[str] = None, value_type: str = "float"
) -> Dict[str, Any]:
    return {
        "name": log_name,
        "description": description,
        "valueType": value_type,
        "dimensions": 1,
        "unit": "m",
        "quantity": None,
        "axis": None,
        "maxSize": 20,
    }
