########################################
#
#  Copyright (C) 2021-     Equinor ASA
#
#  webviz-subsurface is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  webviz-subsurface is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
#  See the GNU General Public License at <http:#www.gnu.org/licenses/gpl.html>
#  for more details.
#
########################################
########################################
#
#  The code in this file is based on and/or inspired by opm-common,
#  which is distributed under the GNU General Public License v3.0,
#  and available at https://github.com/OPM/opm-common.
#
#  Especially in the following points this file, or files imported in this file
#  within the same context, make use of or are based on methods developed
#  for the opm-common project:
#  - Reading of Eclipse INIT files
#  - Units, unit systems and conversion of units
#  - Class structures for storing and accessing PVT data,
#    both base classes and derived classes for specific fluids
#
#  You should have received a copy of the GNU General Public License
#  along with webviz-subsurface. If not, see (https://www.gnu.org/licenses/gpl-3.0.html).
#
#  (12-01-2021)
#
########################################

from typing import Any, Callable, Optional, Tuple, Union

import numpy as np
from opm.io.ecl import EclFile

from ..eclipse_unit import ConvertUnits, CreateUnitConverter, EclUnitEnum, EclUnits
from .pvt_common import (
    EclPhaseIndex,
    EclPropertyTableRawData,
    FluidImplementation,
    InitFileDefinitions,
    PVDx,
    PVTx,
    PvxOBase,
    is_const_compr_index,
    surface_mass_density,
)


class LiveOil(PvxOBase):
    """Class holding a PVT interpolant and access methods for PVT data for live oil

    Attributes:
        interpolant: The interpolant object
    """

    def __init__(
        self,
        index_table: int,
        raw: EclPropertyTableRawData,
        surface_mass_density_oil: float,
        surface_mass_density_gas: float,
        convert: Tuple[
            Callable[
                [
                    float,
                ],
                float,
            ],
            ConvertUnits,
        ],
    ) -> None:
        """Initializes a LiveOil object.

        Creates an interpolant for live oil for the Eclipse data given
        by the raw data in the table with the given index.

        Args:
            index_table: Index of the PVT table
            raw: Eclipse raw data object
            surface_mass_density_oil: Surface mass density of oil
            surface_mass_density_gas: Surface mass density of gas
            convert: Tuple holding a callable and a ConvertUnits object for unit conversions

        """
        self.__interpolant = PVTx(index_table, raw, convert)
        self.__surface_mass_density_oil = surface_mass_density_oil
        self.__surface_mass_density_gas = surface_mass_density_gas

    def formation_volume_factor(
        self, ratio: np.ndarray, pressure: np.ndarray
    ) -> np.ndarray:
        """Args:
            ratio: Ratio (key) values the volume factor values are requested for.
            pressure: Pressure values the volume factor values are requested for.

        Returns:
            Volume factor values for the given ratio and pressure values.

        """
        return self.__interpolant.formation_volume_factor(ratio, pressure)

    def viscosity(self, ratio: np.ndarray, pressure: np.ndarray) -> np.ndarray:
        """Args:
            ratio: Ratio (key) values the viscosity values are requested for.
            pressure: Pressure values the viscosity values are requested for.

        Returns:
            Viscosity values for the given ratio and pressure values.

        """
        return self.__interpolant.viscosity(ratio, pressure)

    def density(self, ratio: np.ndarray, pressure: np.ndarray) -> np.ndarray:
        """Args:
            ratio: Ratio (key) values the density values are requested for.
            pressure: Pressure values the density values are requested for.

        Returns:
            Density values for the given ratio and pressure values.

        """
        # rho_o = (rho_o,sc + Rs * rho_g,sc) / B_o
        fvf_oil = self.formation_volume_factor(ratio, pressure)
        return np.array(
            [
                (
                    self.__surface_mass_density_oil
                    + ratio_sample * self.__surface_mass_density_gas
                )
                / fvf_oil_sample
                for ratio_sample, fvf_oil_sample in zip(ratio, fvf_oil)
            ]
        )

    def get_keys(self) -> np.ndarray:
        """Returns all primary key values (Rs)"""
        return self.__interpolant.get_keys()

    def get_independents(self) -> np.ndarray:
        """Returns all independent pressure values (Po)"""
        return self.__interpolant.get_independents()


class DeadOil(PvxOBase):
    """Class holding a PVT interpolant and access methods for PVT data for dead oil

    Attributes:
        interpolant: The interpolant object
    """

    def __init__(
        self,
        table_index: int,
        raw: EclPropertyTableRawData,
        surface_mass_density_oil: float,
        convert: ConvertUnits,
    ) -> None:
        """Initializes a DeadOil object.

        Creates an interpolant for dead oil for the Eclipse data given
        by the raw data in the table with the given index.

        Args:
            index_table: Index of the PVT table
            raw: Eclipse raw data object
            surface_mass_density_oil: Surface mass density of oil
            convert: ConvertUnits object for unit conversions

        """
        self.__interpolant = PVDx(table_index, raw, convert)
        self.__surface_mass_density_oil = surface_mass_density_oil

    def formation_volume_factor(
        self, ratio: np.ndarray, pressure: np.ndarray
    ) -> np.ndarray:
        """Args:
            ratio: Dummy argument, only to conform to interface of base class.
            pressure: Pressure values the volume factor values are requested for.

        Returns:
            Volume factor values for the given pressure values.

        """
        return self.__interpolant.formation_volume_factor(pressure)

    def viscosity(self, ratio: np.ndarray, pressure: np.ndarray) -> np.ndarray:
        """Args:
            ratio: Dummy argument, only to conform to interface of base class.
            pressure: Pressure values the viscosity values are requested for.

        Returns:
            Viscosity values for the given pressure values.

        """
        return self.__interpolant.viscosity(pressure)

    def density(self, ratio: np.ndarray, pressure: np.ndarray) -> np.ndarray:
        """Args:
            ratio: Dummy argument, only to conform to interface of base class.
            pressure: Pressure values the density values are requested for.

        Returns:
            Density values for the given ratio and pressure values.

        """
        # rho_o = rho_o,sc / B_o
        fvf_oil = self.formation_volume_factor(ratio, pressure)
        return np.array(
            [
                self.__surface_mass_density_oil / fvf_oil_sample
                for fvf_oil_sample in fvf_oil
            ]
        )

    def get_keys(self) -> np.ndarray:
        """Returns all primary keys.

        Since this is dead oil, there is no dependency on Rs.
        Hence, this method returns a list holding floats of value 0.0
        for each independent value.

        """
        return self.__interpolant.get_keys()

    def get_independents(self) -> np.ndarray:
        """Returns all independent pressure values (Po)"""
        return self.__interpolant.get_independents()


class DeadOilConstCompr(PvxOBase):
    """Class holding a PVT interpolant and access methods for PVT data
    for dead oil with constant compressibility"""

    def __init__(
        self,
        index_table: int,
        raw: EclPropertyTableRawData,
        convert: ConvertUnits,
        surface_mass_density_oil: float,
    ) -> None:
        """Initializes a DeadOilConstCompr object.

        Creates an interpolant for dead oil with constant compressibility for the Eclipse data given
        by the raw data in the table with the given index.

        Args:
            index_table: Index of the PVT table
            raw: Eclipse raw data
            convert: Tuple holding a callable and a ConvertUnits object for unit conversions

        Raises:
            ValueError in case of an invalid reference oil pressure
        """
        self.__surface_mass_density_oil = surface_mass_density_oil

        column_stride = raw.num_rows * raw.num_tables * raw.num_primary
        table_stride = raw.num_primary * raw.num_rows
        current_stride = index_table * table_stride

        self.__fvf_ref = convert.column[0](
            raw.data[0 * column_stride + current_stride]
        )  # Bo
        self.__c_o_ref = convert.column[1](
            raw.data[1 * column_stride + current_stride]
        )  # Co
        self.__visc_ref = convert.column[2](
            raw.data[2 * column_stride + current_stride]
        )  # mu_o
        self.__c_v_ref = convert.column[3](
            raw.data[3 * column_stride + current_stride]
        )  # Cv

        self.__p_o_ref = convert.independent(raw.data[current_stride])

        if abs(self.__p_o_ref) < 1.0e20:
            raise ValueError("Invalid Input PVCDO Table")

    def formation_volume_factor(
        self, ratio: np.ndarray, pressure: np.ndarray
    ) -> np.ndarray:
        """Computes formation volume factor values
        for the given pressure values.

        Args:
            ratio: Dummy argument, only to conform to interface of base class
            pressure: Pressure values

        Returns:
            Formation volume factor values for the given pressure values.

        """
        return self.__evaluate(pressure, lambda p: 1.0 / self.__recip_fvf(p))

    def viscosity(self, ratio: np.ndarray, pressure: np.ndarray) -> np.ndarray:
        """Computes viscosity values for the given pressure values.

        Args:
            ratio: Dummy argument, only to conform to interface of base class
            pressure:Pressure values

        Returns:
            Viscosity values corresponding
            to the given pressure values.

        """
        return self.__evaluate(
            pressure, lambda p: self.__recip_fvf(p) / self.__recip_fvf_visc(p)
        )

    def __recip_fvf(self, p_o: float) -> float:
        """Computes the reciprocal of the formation volume factor for the given oil pressure.

        Args:
            p_o: Oil pressure

        Returns:
            Reciprocal of the formation volume factor

        """

        # B_o(P) = B_o(P_ref) * e^-x
        # x = C * (P - P_ref)
        # 1 / B_o(P) = 1 / B_o(P_ref) * e^x

        x = self.__c_o_ref * (p_o - self.__p_o_ref)

        return self.__exp(x) / self.__fvf_ref

    def density(self, ratio: np.ndarray, pressure: np.ndarray) -> np.ndarray:
        """Args:
            ratio: Ratio (key) values the density values are requested for.
            pressure: Pressure values the density values are requested for.

        Returns:
            Density values for the given ratio and pressure values.

        """
        # rho_o = rho_o,sc / B_o
        fvf_oil = self.formation_volume_factor(ratio, pressure)
        return np.array(
            [
                self.__surface_mass_density_oil / fvf_oil_sample
                for fvf_oil_sample in fvf_oil
            ]
        )

    def __recip_fvf_visc(self, p_o: float) -> float:
        """Computes the reciprocal of the product of formation volume factor
        and viscosity for the given oil pressure.

        Args:
            p_o: Oil pressure

        Returns:
            Reciprocal of the product of formation volume factor and viscosity

        """

        # mu_o(P) * B_o(P) = B_o(P_ref) * mu_o(P_ref) * e^-y
        # y = (C - C_v) * (P - P_ref)
        # 1 / (mu_o(P) * B_o(P)) = 1 / (B_o(P_ref) * mu_o(P_ref)) * e^y
        y = (self.__c_o_ref - self.__c_v_ref) * (p_o - self.__p_o_ref)

        return self.__exp(y) / (self.__fvf_ref * self.__visc_ref)

    @staticmethod
    def __exp(x: float) -> float:
        """Internal helper function.

        Computes an approximation to the exponential function by means
        of a Taylor series (to second degree).

        Args:
            x: Expression to use (see manual)

        Returns:
            Approximation to exponential function

        """
        return 1.0 + x * (1.0 + x / 2.0)

    @staticmethod
    def __evaluate(
        pressures: np.ndarray, calculate: Callable[[Any], Any]
    ) -> np.ndarray:
        """Calls the calculate method with each of pressure values and returns the results.

        Args:
            pressures: Pressure values
            calculate: Method to be called with each of the pressure values

        Returns:
            Result values

        """
        return np.array([calculate(pressure) for pressure in pressures])

    def get_keys(self) -> np.ndarray:
        """Returns all primary keys.

        Since this is dead oil, there is no dependency on any ratio.
        Hence, this method returns a list holding a single float of value 0.0.

        """
        return np.zeros(1)

    def get_independents(self) -> np.ndarray:
        """Returns all independent pressure values (Po).

        Since this is water, this does return with only one single pressure value,
        the reference pressure.
        """
        return np.array(
            [
                self.__p_o_ref,
            ]
        )


class Oil(FluidImplementation):
    """Class for storing PVT tables for oil

    Holds a list of regions (one per PVT table).

    Attributes:
        surface_mass_densities: Surface mass densities
        keep_unit_system: True if the original unit system was kept
        original_unit_system: An ErtEclUnitEnum representing the original unit system
    """

    def __init__(
        self,
        raw: EclPropertyTableRawData,
        unit_system: int,
        is_const_compr: bool,
        surface_mass_densities: Tuple[np.ndarray, np.ndarray],
        keep_unit_system: bool = True,
    ):
        """Initializes an Oil object.

        Args:
            raw: Eclipse raw data object
            unit_system: The original unit system
            is_const_compr: True if oil has constant compressibility, else False
            surface_mass_densities: Surface mass densities
            keep_unit_system:
                True if the original unit system shall be kept,
                False if units shall be converted to SI units.

        """
        super().__init__(unit_system, keep_unit_system)
        self.surface_mass_densities = surface_mass_densities
        self.original_unit_system = EclUnitEnum(unit_system)
        self.create_pvt_interpolants(raw, is_const_compr, unit_system)

    def formation_volume_factor_unit(self, latex: bool = False) -> str:
        """Creates and returns the unit symbol of the formation volume factor.

        Args:
            latex: True if the unit symbol shall be returned as LaTeX, False if not.

        Returns:
            The unit symbol of the formation volume factor.

        """
        unit_system = EclUnits.create_unit_system(
            self.original_unit_system
            if self.keep_unit_system
            else EclUnitEnum.ECL_SI_UNITS
        )

        if latex:
            return (
                rf"${{{unit_system.reservoir_volume().symbol}}}/"
                rf"{{{unit_system.surface_volume_liquid().symbol}}}$"
            )
        return (
            f"{unit_system.reservoir_volume().symbol}/"
            f"{unit_system.surface_volume_liquid().symbol}"
        )

    def ratio_unit(self, latex: bool = False) -> str:
        """Creates and returns the unit symbol of the phase ratio.

        Args:
            latex: True if the unit symbol shall be returned as LaTeX, False if not.

        Returns:
            The unit symbol of the phase ratio.

        """
        unit_system = EclUnits.create_unit_system(
            self.original_unit_system
            if self.keep_unit_system
            else EclUnitEnum.ECL_SI_UNITS
        )

        if latex:
            return (
                rf"${{{unit_system.surface_volume_gas().symbol}}}/"
                rf"{{{unit_system.surface_volume_liquid().symbol}}}$"
            )
        return (
            f"{unit_system.surface_volume_gas().symbol}/"
            f"{unit_system.surface_volume_liquid().symbol}"
        )

    def dead_oil_unit_converter(
        self, unit_system: Union[int, EclUnits.UnitSystem]
    ) -> ConvertUnits:
        """Creates a ConvertUnits object for unit conversions for dead oil.

        Args:
            unit_system:
                Either an integer or an enum
                describing the unit system the units are stored in

        Returns:
            ConvertUnits object for unit conversions.

        """
        if not isinstance(unit_system, EclUnits.UnitSystem):
            unit_system = EclUnits.create_unit_system(unit_system)

        return super().pvdx_unit_converter() or ConvertUnits(
            CreateUnitConverter.ToSI.pressure(unit_system),
            [
                CreateUnitConverter.ToSI.recip_fvf(unit_system),
                CreateUnitConverter.ToSI.recip_fvf_visc(unit_system),
                CreateUnitConverter.ToSI.recip_fvf_deriv_press(unit_system),
                CreateUnitConverter.ToSI.recip_fvf_visc_deriv_press(unit_system),
            ],
        )

    def pvcdo_unit_converter(
        self, unit_system: Union[int, EclUnits.UnitSystem]
    ) -> ConvertUnits:
        """Creates a ConvertUnits object for unit conversions
        for dead oil with constant compressibility.

        Args:
            unit_system:
                Either an integer or an enum
                describing the unit system the units are stored in

        Returns:
            ConvertUnits object for unit conversions.

        """
        if not isinstance(unit_system, EclUnits.UnitSystem):
            unit_system = EclUnits.create_unit_system(unit_system)

        return super().pvdx_unit_converter() or ConvertUnits(
            CreateUnitConverter.ToSI.pressure(unit_system),
            [
                CreateUnitConverter.ToSI.fvf(unit_system),
                CreateUnitConverter.ToSI.compressibility(unit_system),
                CreateUnitConverter.ToSI.viscosity(unit_system),
                CreateUnitConverter.ToSI.compressibility(unit_system),
            ],
        )

    def live_oil_unit_converter(
        self, unit_system: Union[int, EclUnits.UnitSystem]
    ) -> Tuple[Callable[[float,], float,], ConvertUnits]:
        """Creates a tuple consisting of a callable and a ConvertUnits object
        for unit conversions for live oil.

        Args:
            unit_system:
                Either an integer or an enum
                describing the unit system the units are stored in

        Returns:
            Tuple consisting of callable and ConvertUnits object

        """
        if not isinstance(unit_system, EclUnits.UnitSystem):
            unit_system = EclUnits.create_unit_system(unit_system)

        return super().pvtx_unit_converter() or (
            CreateUnitConverter.ToSI.dissolved_gas_oil_ratio(unit_system),
            self.dead_oil_unit_converter(unit_system),
        )

    def create_pvt_interpolants(
        self, raw: EclPropertyTableRawData, is_const_compr: bool, unit_system: int
    ) -> None:
        """Creates interpolants for PVT data based on the type of the oil
        (i.e. live, dead and dead with constant compressibility).

        Args:
            raw: Eclipse raw data object
            unit_system: Number describing the unit system the values in the raw data are stored in

        Raises:
            A FluidImplementation.InvalidArgument exception
            in case of a size mismatch in the raw data.

        """
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

        if raw.num_primary == 1:
            self.create_dead_oil(raw, is_const_compr, unit_system)
        else:
            self.create_live_oil(raw, unit_system)

    def create_live_oil(self, raw: EclPropertyTableRawData, unit_system: int) -> None:
        """Creates interpolants for live oil from the given raw Eclipse data and uses
        a live oil unit converter based on the given unit system.

        Args:
            raw: Eclipse raw data object
            unit_system: Integer representation of the unit system used in Eclipse data

        """
        cvrt = self.live_oil_unit_converter(unit_system)

        self._regions = self.make_interpolants_from_raw_data(
            # PKey   Inner   C0     C1         C2           C3
            # Rs     Po      1/B    1/(B*mu)   d(1/B)/dPo   d(1/(B*mu))/dPo
            #        :       :      :          :            :
            raw,
            lambda table_index, raw: LiveOil(
                table_index,
                raw,
                self.surface_mass_densities[0][table_index],
                self.surface_mass_densities[1][table_index],
                cvrt,
            ),
        )

        if len(self.surface_mass_densities[0]) != len(self._regions) or len(
            self.surface_mass_densities[1]
        ) != len(self._regions):
            raise ValueError(
                (
                    "The given Eclipse INIT file seems to be broken"
                    "(number of surface density values does not equal number of PVT regions)."
                )
            )

    def create_dead_oil(
        self, raw: EclPropertyTableRawData, const_compr: bool, unit_system: int
    ) -> None:
        """Creates interpolants for dead oil (with and without constant compressibility)
        from the given raw Eclipse data and uses a dead oil (or pvcdo) unit converter
        based on the given unit system.

        Args:
            raw: Eclipse raw data object
            unit_system: Integer representation of the unit system used in Eclipse data

        """
        if const_compr:
            cvrt = self.pvcdo_unit_converter(unit_system)

            self._regions = self.make_interpolants_from_raw_data(
                raw,
                lambda table_index, raw: DeadOilConstCompr(
                    table_index, raw, cvrt, self.surface_mass_densities[0][table_index]
                ),
            )
            return

        cvrt = self.dead_oil_unit_converter(unit_system)

        self._regions = self.make_interpolants_from_raw_data(
            raw,
            lambda table_index, raw: DeadOil(
                table_index, raw, self.surface_mass_densities[0][table_index], cvrt
            ),
        )

    def is_live_oil(self) -> bool:
        """Checks if this fluid is live oil.

        Returns:
            True if live oil, else False

        """
        if len(self._regions) > 0:
            return isinstance(self._regions[0], LiveOil)
        return False

    def is_dead_oil(self) -> bool:
        """Checks if this fluid is dead oil with variable compressibility.

        Returns:
            True if dead oil with variable compressibility, else False

        """
        if len(self._regions) > 0:
            return isinstance(self._regions[0], DeadOil)
        return False

    def is_dead_oil_const_compr(self) -> bool:
        """Checks if this fluid is dead oil with constant compressibility.

        Returns:
            True if dead oil with constant compressibility, else False

        """
        if len(self._regions) > 0:
            return isinstance(self._regions[0], DeadOilConstCompr)
        return False

    @staticmethod
    def from_ecl_init_file(
        ecl_init_file: EclFile, keep_unit_system: bool = False
    ) -> Optional["Oil"]:
        """Reads the given Eclipse file and creates an Oil object from its data.

        Args:
            ecl_init_file: Eclipse INIT file
            keep_unit_system:
                Set to True if the unit system used in the Eclipse file
                shall be kept, False if SI shall be used.

        Returns:
            An Oil object or None if the data in the Eclipse file was invalid

        """
        intehead = ecl_init_file.__getitem__(InitFileDefinitions.INTEHEAD_KW)

        logihead = ecl_init_file.__getitem__(InitFileDefinitions.LOGIHEAD_KW)
        is_is_const_compr = bool(logihead[is_const_compr_index()])

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

        surface_mass_densities = (
            surface_mass_density(ecl_init_file, EclPhaseIndex.LIQUID, keep_unit_system),
            surface_mass_density(ecl_init_file, EclPhaseIndex.VAPOUR, keep_unit_system),
        )

        return Oil(
            raw,
            intehead[InitFileDefinitions.INTEHEAD_UNIT_INDEX],
            is_is_const_compr,
            surface_mass_densities,
            keep_unit_system,
        )
