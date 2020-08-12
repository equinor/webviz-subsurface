########################################
#
#  Copyright (C) 2020-     Equinor ASA
#
########################################

import pandas as pd
from opm.io.ecl import EclFile

from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore

from .opm_init_io import Oil, Gas, Water, DryGas

try:
    from .fmu_input import load_ensemble_set
except ImportError:
    from fmu_input import load_ensemble_set

try:
    import ecl2df
except ImportError:
    pass


def read_init_file(ecl_files: ecl2df.EclFiles):
    # pylint: disable-msg=too-many-locals
    ecl_init_file = EclFile(ecl_files.get_initfile().get_filename())

    oil = Oil.from_ecl_init_file(ecl_init_file)
    gas = Gas.from_ecl_init_file(ecl_init_file)
    water = Water.from_ecl_init_file(ecl_init_file)

    column_pvtnum = []
    column_oil_gas_ratio = []
    column_volume_factor = []
    column_pressure = []
    column_viscosity = []
    column_keyword = []

    for table_index, table in enumerate(oil.tables()):
        for outer_pair in table.get_values():
            for inner_pair in outer_pair.y:
                column_pvtnum.append(table_index + 1)
                column_keyword.append("PVTO")
                column_oil_gas_ratio.append(outer_pair.x)
                column_pressure.append(inner_pair.x)
                column_volume_factor.append(1 / inner_pair.y[0])
                column_viscosity.append(inner_pair.y[0] / inner_pair.y[1])

    for table_index, table in enumerate(gas.tables()):
        for outer_pair in table.get_values():
            for inner_pair in outer_pair.y:
                column_pvtnum.append(table_index + 1)
                column_keyword.append("PVDG")
                if isinstance(table, DryGas):
                    column_oil_gas_ratio.append(0)
                else:
                    column_oil_gas_ratio.append(outer_pair.x)
                column_pressure.append(inner_pair.x)
                column_volume_factor.append(1 / inner_pair.y[0])
                column_viscosity.append(inner_pair.y[0] / inner_pair.y[1])

    for table_index, table in enumerate(water.tables()):
        for outer_pair in table.get_values():
            for inner_pair in outer_pair.y:
                column_pvtnum.append(table_index + 1)
                column_keyword.append("PVTW")
                column_oil_gas_ratio.append(outer_pair.x)
                column_pressure.append(inner_pair.x)
                column_volume_factor.append(1 / inner_pair.y[0])
                column_viscosity.append(1.0 / inner_pair.y[2] * inner_pair.y[0])

    data_frame = pd.DataFrame(
        {
            "PVTNUM": column_pvtnum,
            "KEYWORD": column_keyword,
            "RS": column_oil_gas_ratio,
            "PRESSURE": column_pressure,
            "VOLUMEFACTOR": column_volume_factor,
            "VISCOSITY": column_viscosity,
        }
    )

    return data_frame


if __name__ == "__main__":
    read_init_file(
        ecl2df.EclFiles(
            "../../webviz-subsurface-testdata/reek_history_match/"
            "realization-0/iter-0/eclipse/model/5_R001_REEK-0.DATA"
        )
    )
else:

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    @webvizstore
    def load_pvt_dataframe(
        ensemble_paths: dict,
        ensemble_set_name: str = "EnsembleSet",
        use_init_file: bool = False,
    ) -> pd.DataFrame:
        def ecl2df_pvt_dataframe(kwargs) -> pd.DataFrame:
            return ecl2df.pvt.df(kwargs["realization"].get_eclfiles())

        def init_to_pvt_dataframe(kwargs) -> pd.DataFrame:
            return read_init_file(kwargs["realization"].get_eclfiles())

        return load_ensemble_set(ensemble_paths, ensemble_set_name).apply(
            init_to_pvt_dataframe if use_init_file else ecl2df_pvt_dataframe
        )
