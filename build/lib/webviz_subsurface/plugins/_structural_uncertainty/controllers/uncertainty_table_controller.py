from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from dash import Dash, Input, Output, State
from dash.exceptions import PreventUpdate

from webviz_subsurface._models import SurfaceSetModel, WellSetModel


def update_uncertainty_table(
    app: Dash,
    get_uuid: Callable,
    surface_set_models: Dict[str, SurfaceSetModel],
    well_set_model: WellSetModel,
) -> None:
    @app.callback(
        Output({"id": get_uuid("uncertainty-table"), "element": "table"}, "data"),
        Output({"id": get_uuid("uncertainty-table"), "element": "label"}, "children"),
        Input(
            {"id": get_uuid("uncertainty-table"), "element": "apply-button"}, "n_clicks"
        ),
        State({"id": get_uuid("intersection-data"), "element": "well"}, "value"),
        State(
            {"id": get_uuid("intersection-data"), "element": "surface_attribute"},
            "value",
        ),
        State(
            {"id": get_uuid("intersection-data"), "element": "surface_names"}, "value"
        ),
        State({"id": get_uuid("intersection-data"), "element": "ensembles"}, "value"),
        State(get_uuid("realization-store"), "data"),
    )
    # pylint: disable=too-many-locals
    def _update_uncertainty_table(
        apply_btn: Optional[int],
        wellname: str,
        surface_attribute: str,
        surface_names: List[str],
        ensembles: List[str],
        realizations: List[int],
    ) -> Tuple[List, str]:
        if apply_btn is None:
            raise PreventUpdate
        dframes = []

        well = well_set_model.get_well(wellname)
        realizations = [int(real) for real in realizations]
        for ensemble in ensembles:
            surfset = surface_set_models[ensemble]
            for surfacename in surface_names:
                for calculation in ["Mean", "Min", "Max"]:
                    surface = surfset.calculate_statistical_surface(
                        name=surfacename,
                        attribute=surface_attribute,
                        calculation=calculation,
                        realizations=realizations,
                    )

                    with np.errstate(invalid="ignore"):
                        surface_picks = well.get_surface_picks(surface)
                        if surface_picks is None:
                            continue
                        surface_df = surface_picks.dataframe.drop(
                            columns=["X_UTME", "Y_UTMN", "DIRECTION", "WELLNAME"]
                        )
                        tvds = (
                            surface_df["Z_TVDSS"]
                            .apply(lambda x: np.round(x, 1))
                            .tolist()
                        )

                        surface_df.rename({well.mdlogname: "MD"}, axis=1, inplace=True)
                        # Do not calculate MD if Well tvd is truncated
                        mds = (
                            surface_df["MD"].apply(lambda x: np.round(x, 1)).tolist()
                            if not well_set_model.is_truncated
                            else []
                        )

                        surface_df["Pick no"] = surface_df.index + 1
                        pick_nos = surface_df["Pick no"].tolist()

                        data = {
                            "TVD": " / ".join(str(x) for x in tvds),
                            "MD": " / ".join(str(x) for x in mds),
                            "Pick no": " / ".join(str(x) for x in pick_nos),
                            "Surface name": surfacename,
                            "Calculation": calculation,
                            "Ensemble": ensemble,
                        }
                        surface_df = pd.DataFrame([data])
                        dframes.append(surface_df)

        dframe = (
            pd.concat(dframes)
            if dframes
            else pd.DataFrame(
                [
                    {
                        "TVD": "-",
                        "MD": "-",
                        "Pick no": "-",
                        "Surface name": "-",
                        "Calculation": "-",
                        "Ensemble": "-",
                    }
                ]
            )
        )
        return dframe.to_dict("records"), f"Statistics for well {wellname}"
