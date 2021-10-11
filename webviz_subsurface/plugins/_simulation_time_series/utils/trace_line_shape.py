from typing import Optional


def get_simulation_line_shape(
    line_shape_fallback: str, vector: str, vector_smry_meta: Optional[dict] = None
) -> str:
    """Get simulation time series line shape, smry_meta is a dict on the format given
    by `_create_smry_meta_dict` in `webviz-subsurface/webviz_subsurface/ert_jobs/smry2arrow.py`.
    """
    if vector.startswith("AVG_") or vector.startswith("INTVL_"):
        # These custom calculated vectors are valid forwards in time.
        return "hv"

    if vector_smry_meta is None:
        return line_shape_fallback
    try:
        if vector_smry_meta["is_rate"]:
            # Eclipse rate vectors are valid backwards in time.
            return "vh"
        if vector_smry_meta["is_total"]:
            return "linear"
    except (AttributeError, KeyError):
        pass
    return line_shape_fallback
