from typing import Callable, Dict, Optional, Union

import webviz_core_components as wcc

from ..models import (
    PropertyStatisticsModel,
    ProviderTimeSeriesDataModel,
    SimulationTimeSeriesModel,
)
from .property_delta_view import property_delta_view
from .property_qc_view import property_qc_view
from .property_response_view import property_response_view


def main_view(
    get_uuid: Callable,
    property_model: PropertyStatisticsModel,
    vector_model: Optional[
        Union[SimulationTimeSeriesModel, ProviderTimeSeriesDataModel]
    ],
    surface_folders: Optional[Dict] = None,
) -> wcc.Tabs:
    tabs = [
        wcc.Tab(
            label="Property QC",
            children=property_qc_view(get_uuid=get_uuid, property_model=property_model),
        )
    ]
    if len(property_model.ensembles) > 1:
        tabs.append(
            wcc.Tab(
                label="AHM impact on property",
                children=property_delta_view(
                    get_uuid=get_uuid,
                    property_model=property_model,
                    surface_folders=surface_folders,
                ),
            )
        )
    if vector_model is not None:
        tabs.append(
            wcc.Tab(
                label="Property impact on simulation profiles",
                children=property_response_view(
                    get_uuid=get_uuid,
                    property_model=property_model,
                    vector_model=vector_model,
                    surface_folders=surface_folders,
                ),
            ),
        )

    return wcc.Tabs(style={"width": "100%"}, children=tabs)
