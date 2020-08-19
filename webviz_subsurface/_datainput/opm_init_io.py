########################################
#
#  Copyright (C) 2020-     Equinor ASA
#
########################################

from enum import Enum
from typing import List, Optional

from opm.io.ecl import EclFile


class InitFileDefinitions:  # pylint: disable=too-few-public-methods
    """
    A namespace for constant definitions for
    reading Eclipse INIT files.
    """

    LOGIHEAD_KW = "LOGIHEAD"
    INTEHEAD_KW = "INTEHEAD"
    INTEHEAD_UNIT_INDEX = 2
    INTEHEAD_PHASE_INDEX = 14
    LOGIHEAD_RS_INDEX = 0
    LOGIHEAD_RV_INDEX = 1
    TABDIMS_IBPVTO_OFFSET_ITEM = 6
    TABDIMS_JBPVTO_OFFSET_ITEM = 7
    TABDIMS_NRPVTO_ITEM = 8
    TABDIMS_NPPVTO_ITEM = 9
    TABDIMS_NTPVTO_ITEM = 10
    TABDIMS_IBPVTW_OFFSET_ITEM = 11
    TABDIMS_IBPVTG_OFFSET_ITEM = 13
    TABDIMS_JBPVTG_OFFSET_ITEM = 14
    TABDIMS_NRPVTG_ITEM = 15
    TABDIMS_NPPVTG_ITEM = 16
    TABDIMS_NTPVTG_ITEM = 17
    LOGIHEAD_CONSTANT_OILCOMPR_INDEX = 39 - 1

    TABDIMS_IBDENS_OFFSET_ITEM = 18
    TABDIMS_NTDENS_ITEM = 19


class EclPhaseIndex(Enum):
    Aqua = 0
    Liquid = 1
    Vapour = 2


class EclPropertyTableRawData:  # pylint: disable=too-few-public-methods
    """
    A structure for storing read
    INIT file data.
    """

    def __init__(self):
        self.data = []
        self.primary_key = []
        self.num_primary = 0
        self.num_rows = 0
        self.num_cols = 0
        self.num_tables = 0


def const_compr_index() -> int:
    return InitFileDefinitions.LOGIHEAD_CONSTANT_OILCOMPR_INDEX


def surface_mass_density(ecl_file: EclFile, phase: EclPhaseIndex) -> List[float]:
    if phase is EclPhaseIndex.Liquid:
        col = 0
    elif phase is EclPhaseIndex.Aqua:
        col = 1
    elif phase is EclPhaseIndex.Vapour:
        col = 2
    else:
        col = -1

    if col == -1:
        raise AttributeError("Phase must be Liquid, Aqua or Vapour.")

    tabdims = ecl_file.__getitem__("TABDIMS")
    tab = ecl_file.__getitem__("TAB")

    start = tabdims[InitFileDefinitions.TABDIMS_IBDENS_OFFSET_ITEM] - 1
    nreg = tabdims[InitFileDefinitions.TABDIMS_NTDENS_ITEM]

    rho = [tab[start + nreg * (col + 0)], tab[start + nreg * (col + 1)]]

    return rho


class VariateAndValues:  # pylint: disable=too-few-public-methods
    """
    A structure for holding a variate and
    multiple covariates.
    """

    def __init__(self):
        self.x = 0
        self.y = []


class PvxOBase:
    """
    A base class for all fluids.
    """

    def __init__(self, values: List[VariateAndValues]):
        self.values = values

    def get_values(self):
        return self.values

    # pylint: disable=R0201
    def formation_volume_factor(
        self, gas_oil_ratio: List[float], pressure: List[float]
    ) -> List[float]:
        """
        Does only return an empty list for now.
        """
        if len(gas_oil_ratio) != len(pressure):
            raise ValueError("rs and po arguments must be of same size")
        return []

    def viscosity(
        self, gas_oil_ratio: List[float], pressure: List[float]
    ) -> List[float]:
        pass


class LiveOil(PvxOBase):
    pass


class WetGas(PvxOBase):
    pass


class DryGas(PvxOBase):
    pass


class WaterImpl(PvxOBase):
    pass


class Implementation:
    class InvalidArgument(Exception):
        def __init__(self, message: str):
            self.message = message
            super().__init__(message)

    class InvalidType(Exception):
        def __init__(self):
            super().__init__("Invalid type. Only live oil/wet gas/water supported.")

    def __init__(self):
        self.values = []

    def get_table(self, tab_index: int) -> Optional[List[VariateAndValues]]:
        if tab_index in range(0, len(self.values)):
            return self.values[tab_index]

        return None

    def tables(self) -> List[PvxOBase]:
        return self.values

    @staticmethod
    def entry_valid(x: float) -> bool:
        # Equivalent to ECLPiecewiseLinearInterpolant.hpp line 293
        # or ECLPvtOil.cpp line 458
        return abs(x) < 1.0e20


class Oil(Implementation):
    def __init__(
        self, raw: EclPropertyTableRawData, const_compr: bool, rhos: List[float]
    ):
        super().__init__()
        self.rhos = rhos
        self.values = self.create_pvt_function(raw, const_compr)

    # pylint: disable=unused-argument
    def create_pvt_function(
        self, raw: EclPropertyTableRawData, const_compr: bool
    ) -> List[PvxOBase]:
        if raw.num_primary == 0:
            raise super().InvalidArgument("Oil PVT table without primary lookup key")
        if raw.num_cols != 5:
            raise super().InvalidArgument("PVT table for oil must have five columns")
        if len(raw.primary_key) != (raw.num_primary * raw.num_tables):
            raise super().InvalidArgument(
                "Size mismatch in RS nodes of PVT table for oil"
            )
        if len(raw.data) != (
            raw.num_primary * raw.num_rows * raw.num_cols * raw.num_tables
        ):
            raise super().InvalidArgument(
                "Size mismatch in Condensed table data of PVT table for oil"
            )

        # For now, raise an exception if dead oil, since this is not supported yet
        if raw.num_primary == 1:
            raise super().InvalidType()

        return self.create_live_oil(raw)

    def create_live_oil(self, raw: EclPropertyTableRawData) -> List[PvxOBase]:
        # Holding raw.num_tables values
        ret = []

        column_stride = raw.num_rows * raw.num_tables * raw.num_primary
        table_stride = raw.num_primary * raw.num_rows

        # pylint: disable=too-many-nested-blocks
        for index_table in range(0, raw.num_tables):
            values = []

            # PKey  Inner   C0  C1          C2          C3
            # Rs    Po      1/B 1/(B*mu)    d(1/B)/dPo  d(1/(B*mu))/dPo

            for index_primary in range(0, raw.num_primary):
                if self.entry_valid(raw.primary_key[index_primary]):
                    outer_value_pair = VariateAndValues()
                    outer_value_pair.x = raw.primary_key[index_primary]
                    for index_row in range(0, raw.num_rows):
                        pressure = raw.data[
                            column_stride * 0
                            + index_table * table_stride
                            + index_primary * raw.num_rows
                            + index_row
                        ]
                        if self.entry_valid(pressure):
                            inner_value_pair = VariateAndValues()
                            inner_value_pair.x = pressure
                            inner_value_pair.y = [0 for col in range(1, raw.num_cols)]
                            for index_column in range(1, raw.num_cols):
                                inner_value_pair.y[index_column - 1] = raw.data[
                                    column_stride * index_column
                                    + index_table * table_stride
                                    + index_primary * raw.num_rows
                                    + index_row
                                ]
                            outer_value_pair.y.append(inner_value_pair)
                        else:
                            break
                else:
                    break

                values.append(outer_value_pair)
            ret.append(LiveOil(values))

        return ret

    @staticmethod
    def from_ecl_init_file(ecl_init_file: EclFile) -> Optional["Oil"]:
        logihead = ecl_init_file.__getitem__(InitFileDefinitions.LOGIHEAD_KW)
        is_const_compr = bool(logihead[const_compr_index()])

        raw = EclPropertyTableRawData()

        tab_dims = ecl_init_file.__getitem__("TABDIMS")
        tab = ecl_init_file.__getitem__("TAB")

        num_rs = tab_dims[InitFileDefinitions.TABDIMS_NRPVTO_ITEM]

        raw.num_rows = tab_dims[InitFileDefinitions.TABDIMS_NPPVTO_ITEM]
        raw.num_cols = 5
        raw.num_tables = tab_dims[InitFileDefinitions.TABDIMS_NTPVTO_ITEM]

        if raw.num_tables == 0:
            return None

        if logihead[InitFileDefinitions.LOGIHEAD_RS_INDEX]:
            raw.num_primary = num_rs

        else:
            raw.num_primary = 1

        num_tab_elements = raw.num_primary * raw.num_tables
        start = tab_dims[InitFileDefinitions.TABDIMS_JBPVTO_OFFSET_ITEM] - 1
        raw.primary_key = tab[start : start + num_tab_elements]

        num_tab_elements = (
            raw.num_primary * raw.num_rows * raw.num_cols * raw.num_tables
        )
        start = tab_dims[InitFileDefinitions.TABDIMS_IBPVTO_OFFSET_ITEM] - 1
        raw.data = tab[start : start + num_tab_elements]

        rhos = surface_mass_density(ecl_init_file, EclPhaseIndex.Liquid)

        return Oil(raw, is_const_compr, rhos)


class Gas(Implementation):
    def __init__(self, raw: EclPropertyTableRawData, rhos: List[float]):
        super().__init__()
        self.rhos = rhos
        self.values = self.create_pvt_function(raw)

    def create_pvt_function(self, raw: EclPropertyTableRawData) -> List[PvxOBase]:
        if raw.num_primary == 0:
            raise super().InvalidArgument("Gas PVT table without primary lookup key")
        if raw.num_cols != 5:
            raise super().InvalidArgument("PVT table for gas must have five columns")
        if len(raw.primary_key) != (raw.num_primary * raw.num_tables):
            raise super().InvalidArgument(
                "Size mismatch in Pressure nodes of PVT table for gas"
            )
        if len(raw.data) != (
            raw.num_primary * raw.num_rows * raw.num_cols * raw.num_tables
        ):
            raise super().InvalidArgument(
                "Size mismatch in Condensed table data of PVT table for gas"
            )

        if raw.num_primary == 1:
            return self.create_dry_gas(raw)

        return self.create_wet_gas(raw)

    def create_dry_gas(self, raw: EclPropertyTableRawData) -> List[PvxOBase]:
        # Holding raw.num_tables values
        ret = []

        column_stride = raw.num_rows * raw.num_tables * raw.num_primary
        table_stride = raw.num_primary * raw.num_rows

        # pylint: disable=too-many-nested-blocks
        for index_table in range(0, raw.num_tables):
            values = []

            # PKey  Inner   C0  C1          C2          C3
            # Rs    Po      1/B 1/(B*mu)    d(1/B)/dPo  d(1/(B*mu))/dPo

            for index_primary in range(0, raw.num_primary):
                if self.entry_valid(raw.primary_key[index_primary]):
                    outer_value_pair = VariateAndValues()
                    outer_value_pair.x = raw.primary_key[index_primary]
                    for index_row in range(0, raw.num_rows):
                        pressure = raw.data[
                            column_stride * 0
                            + index_table * table_stride
                            + index_primary * raw.num_rows
                            + index_row
                        ]
                        if self.entry_valid(pressure):
                            inner_value_pair = VariateAndValues()
                            inner_value_pair.x = pressure
                            inner_value_pair.y = [0 for col in range(1, raw.num_cols)]
                            for index_column in range(1, raw.num_cols):
                                inner_value_pair.y[index_column - 1] = raw.data[
                                    column_stride * index_column
                                    + index_table * table_stride
                                    + index_primary * raw.num_rows
                                    + index_row
                                ]
                            outer_value_pair.y.append(inner_value_pair)
                        else:
                            break
                else:
                    break

                values.append(outer_value_pair)

            ret.append(DryGas(values))

        return ret

    def create_wet_gas(self, raw: EclPropertyTableRawData) -> List[PvxOBase]:
        # Holding raw.num_tables values
        ret = []

        column_stride = raw.num_rows * raw.num_tables * raw.num_primary
        table_stride = raw.num_primary * raw.num_rows

        # pylint: disable=too-many-nested-blocks
        for index_table in range(0, raw.num_tables):
            values = []

            # PKey  Inner   C0  C1          C2          C3
            # Rs    Po      1/B 1/(B*mu)    d(1/B)/dPo  d(1/(B*mu))/dPo

            for index_primary in range(0, raw.num_primary):
                if self.entry_valid(raw.primary_key[index_primary]):
                    outer_value_pair = VariateAndValues()
                    outer_value_pair.x = raw.primary_key[index_primary]
                    for index_row in range(0, raw.num_rows):
                        pressure = raw.data[
                            column_stride * 0
                            + index_table * table_stride
                            + index_primary * raw.num_rows
                            + index_row
                        ]
                        if self.entry_valid(pressure):
                            inner_value_pair = VariateAndValues()
                            inner_value_pair.x = pressure
                            inner_value_pair.y = [0 for col in range(1, raw.num_cols)]
                            for index_column in range(1, raw.num_cols):
                                inner_value_pair.y[index_column - 1] = raw.data[
                                    column_stride * index_column
                                    + index_table * table_stride
                                    + index_primary * raw.num_rows
                                    + index_row
                                ]
                            outer_value_pair.y.append(inner_value_pair)
                        else:
                            break
                else:
                    break

                values.append(outer_value_pair)

            ret.append(WetGas(values))

        return ret

    @staticmethod
    def from_ecl_init_file(ecl_init_file: EclFile) -> Optional["Gas"]:
        intehead = ecl_init_file.__getitem__(InitFileDefinitions.INTEHEAD_KW)
        intehead_phase = intehead[InitFileDefinitions.INTEHEAD_PHASE_INDEX]

        if (intehead_phase & (1 << 2)) == 0:
            return None

        raw = EclPropertyTableRawData()

        tab_dims = ecl_init_file.__getitem__("TABDIMS")
        tab = ecl_init_file.__getitem__("TAB")

        num_rv = tab_dims[InitFileDefinitions.TABDIMS_NRPVTG_ITEM]
        num_pg = tab_dims[InitFileDefinitions.TABDIMS_NPPVTG_ITEM]

        raw.num_cols = 5
        raw.num_tables = tab_dims[InitFileDefinitions.TABDIMS_NTPVTG_ITEM]

        if raw.num_tables == 0:
            return None

        logihead = ecl_init_file.__getitem__(InitFileDefinitions.LOGIHEAD_KW)

        if logihead[InitFileDefinitions.LOGIHEAD_RV_INDEX]:
            raw.num_primary = num_pg
            raw.num_rows = num_rv

        else:
            raw.num_primary = 1
            raw.num_rows = num_pg

        num_tab_elements = raw.num_primary * raw.num_tables
        start = tab_dims[InitFileDefinitions.TABDIMS_JBPVTG_OFFSET_ITEM] - 1
        raw.primary_key = tab[start : start + num_tab_elements]

        num_tab_elements = (
            raw.num_primary * raw.num_rows * raw.num_cols * raw.num_tables
        )
        start = tab_dims[InitFileDefinitions.TABDIMS_IBPVTG_OFFSET_ITEM] - 1
        raw.data = tab[start : start + num_tab_elements]

        rhos = surface_mass_density(ecl_init_file, EclPhaseIndex.Vapour)

        return Gas(raw, rhos)


class Water(Implementation):
    def __init__(self, raw: EclPropertyTableRawData, rhos: List[float]):
        super().__init__()
        self.rhos = rhos
        self.values = self.create_water(raw)

    def create_water(self, raw: EclPropertyTableRawData) -> List[PvxOBase]:
        # Holding raw.num_tables values
        ret = []

        column_stride = raw.num_rows * raw.num_tables * raw.num_primary
        table_stride = raw.num_primary * raw.num_rows

        for index_table in range(0, raw.num_tables):
            values = []

            # PKey  Inner   C0  C1          C2          C3
            # Rs    Po      1/B 1/(B*mu)    d(1/B)/dPo  d(1/(B*mu))/dPo

            index_primary = 0
            outer_value_pair = VariateAndValues()
            outer_value_pair.x = 0
            for index_row in range(0, raw.num_rows):
                pressure = raw.data[
                    column_stride * 0
                    + index_table * table_stride
                    + index_primary * raw.num_rows
                    + index_row
                ]
                if self.entry_valid(pressure):
                    inner_value_pair = VariateAndValues()
                    inner_value_pair.x = pressure
                    inner_value_pair.y = [0 for col in range(1, raw.num_cols)]
                    for index_column in range(1, raw.num_cols):
                        inner_value_pair.y[index_column - 1] = raw.data[
                            column_stride * index_column
                            + index_table * table_stride
                            + index_primary * raw.num_rows
                            + index_row
                        ]
                    outer_value_pair.y.append(inner_value_pair)
                else:
                    break

                values.append(outer_value_pair)

            ret.append(WaterImpl(values))

        return ret

    @staticmethod
    def from_ecl_init_file(ecl_init_file: EclFile) -> Optional["Water"]:
        intehead = ecl_init_file.__getitem__(InitFileDefinitions.INTEHEAD_KW)
        intehead_phase = intehead[InitFileDefinitions.INTEHEAD_PHASE_INDEX]

        if (intehead_phase & (1 << 2)) == 0:
            return None

        raw = EclPropertyTableRawData()

        tab_dims = ecl_init_file.__getitem__("TABDIMS")
        tab = ecl_init_file.__getitem__("TAB")

        raw.num_primary = 1
        raw.num_rows = 1
        raw.num_cols = 5
        raw.num_tables = tab_dims[InitFileDefinitions.TABDIMS_NTPVTG_ITEM]

        if raw.num_tables == 0:
            return None

        num_tab_elements = (
            raw.num_primary * raw.num_rows * raw.num_cols * raw.num_tables
        )
        start = tab_dims[InitFileDefinitions.TABDIMS_IBPVTW_OFFSET_ITEM] - 1
        raw.data = tab[start : start + num_tab_elements]

        rhos = surface_mass_density(ecl_init_file, EclPhaseIndex.Aqua)

        return Water(raw, rhos)
