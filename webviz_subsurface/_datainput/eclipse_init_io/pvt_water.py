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

from typing import Any, Callable, List, Optional, Union

import numpy as np
from opm.io.ecl import EclFile

from ..eclipse_unit import ConvertUnits, CreateUnitConverter, EclUnitEnum, EclUnits
from .pvt_common import (
    EclPhaseIndex,
    EclPropertyTableRawData,
    FluidImplementation,
    InitFileDefinitions,
    PvxOBase,
    surface_mass_density,
)


class WaterImpl(PvxOBase):
    """Class holding a PVT interpolant and access methods for PVT data for water"""

    def __init__(
        self,
        index_table: int,
        raw: EclPropertyTableRawData,
        surface_mass_density_water: float,
        convert: ConvertUnits,
    ) -> None:
        """Initializes a Water object.

        Creates an interpolant for Water for the Eclipse data given
        by the raw data in the table with the given index.

        Args:
            index_table: Index of the PVT table
            raw: Eclipse raw data
            surface_mass_density_water: Surface mass density of water
            convert: Tuple holding a callable and a ConvertUnits object for unit conversions

        """
        column_stride = raw.num_rows * raw.num_tables * raw.num_primary
        table_stride = raw.num_primary * raw.num_rows
        current_stride = index_table * table_stride

        # [ Pw, 1/Bw, Cw, 1/(Bw*mu_w), Cw - Cv ]
        self.__pw_ref = convert.independent(raw.data[current_stride])
        self.__recip_fvf_ref = convert.column[0](
            raw.data[current_stride + 1 * column_stride]
        )
        self.__c_w_ref = convert.column[1](raw.data[current_stride + 2 * column_stride])
        self.__recip_fvf_visc_ref = convert.column[2](
            raw.data[current_stride + 3 * column_stride]
        )
        self.__diff_cw_cv_ref = convert.column[3](
            raw.data[current_stride + 4 * column_stride]
        )

        self.__surface_mass_density_water = surface_mass_density_water

    def __recip_fvf(self, p_w: float) -> float:
        """Computes the reciprocal of the formation volume factor for the given water pressure.

        Args:
            p_w: Water pressure

        Returns:
            Reciprocal of the formation volume factor

        """

        # B_w(P) = (B_w(P_ref)) / (1 + x + (x^2 / 2))
        # x = C * (P - P_ref)
        # NOTE: Don't forget that all values in INIT files are stored as reciprocals!
        # 1 / B_w(P) = 1 / B_w(P_ref) * (1 + x + x^2 / 2)

        x = self.__c_w_ref * (p_w - self.__pw_ref)

        return self.__recip_fvf_ref * self.__exp(x)

    def __recip_fvf_visc(self, p_w: float) -> float:
        """Computes the reciprocal of the product of formation volume factor
        and viscosity for the given water pressure.

        Args:
            p_w: Water pressure

        Returns:
            Reciprocal of the product of formation volume factor and viscosity

        """

        # mu_w(P) * B_w(P) = B_w(P_ref) * mu_w(P_ref) / (1 + y + (y^2 / 2))
        # y = (C - C_v) * (P - P_ref)
        # NOTE: Don't forget that all values in INIT files are stored as reciprocals!
        # 1 / (mu_w(P) * B_w(P)) = 1 / (B_w(P_ref) * mu_w(P_ref)) * (1 + y + (y^2 / 2))

        y = self.__diff_cw_cv_ref * (p_w - self.__pw_ref)

        return self.__recip_fvf_visc_ref * self.__exp(y)

    @staticmethod
    def __evaluate(
        pressures: np.ndarray, calculate: Callable[[Any], Any]
    ) -> np.ndarray:
        """Calls the calculate method with each of the pressure values
        and returns the results.

        Args:
            pressures: Pressure values
            calculate: Method to be called with each of the pressure values

        Returns:
            Result values

        """
        return np.array([calculate(pressure) for pressure in pressures])

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
            pressure: Pressure values

        Returns:
            Viscosity values for the given pressure values.

        """
        return self.__evaluate(
            pressure, lambda p: self.__recip_fvf(p) / self.__recip_fvf_visc(p)
        )

    def density(self, ratio: np.ndarray, pressure: np.ndarray) -> np.ndarray:
        """Args:
            ratio: Dummy argument, only to conform to interface of base class.
            pressure: Pressure values the density values are requested for.

        Returns:
            Density values for the given ratio and pressure values.

        """
        # rho_w = rho_w,sc / B_w
        fvf_water = self.formation_volume_factor(ratio, pressure)
        return np.array(
            [
                self.__surface_mass_density_water / fvf_water_sample
                for fvf_water_sample in fvf_water
            ]
        )

    def get_keys(self) -> np.ndarray:
        """Returns all primary keys.

        Since this is water, there is no dependency on any ratio.
        Hence, this method returns a list holding a single float of value 0.0.

        """
        return np.zeros(1)

    def get_independents(self) -> np.ndarray:
        """Returns all independent pressure values (Pw).

        Since this is water, this does return with only one single pressure value,
        the reference pressure.
        """
        return np.array(
            [
                self.__pw_ref,
            ]
        )


class Water(FluidImplementation):
    """Class for storing PVT tables for water

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
        surface_mass_densities: np.ndarray,
        keep_unit_system: bool = True,
    ):
        """Initializes a Water object.

        Args:
            raw: Eclipse raw data object
            unit_system: The original unit system
            surface_mass_densities: Surface mass densities
            keep_unit_system:
                True if the original unit system shall be kept,
                False if units shall be converted to SI units.

        """
        super().__init__(keep_unit_system)
        self.surface_mass_densities = surface_mass_densities
        self.original_unit_system = EclUnitEnum(unit_system)
        self.create_water(raw, unit_system)

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
                rf"${{{unit_system.reservoir_volume().symbol}}}"
                rf"/{{{unit_system.surface_volume_liquid().symbol}}}$"
            )
        return (
            f"{unit_system.reservoir_volume().symbol}"
            f"/{unit_system.surface_volume_liquid().symbol}"
        )

    def ratio_unit(self, latex: bool = False) -> str:
        """Creates and returns the unit symbol of the phase ratio.

        Args:
            latex: True if the unit symbol shall be returned as LaTeX, False if not.

        Returns:
            The unit symbol of the phase ratio.

        """
        raise NotImplementedError("Water does not have a phase ratio unit.")

    def water_unit_converter(
        self, unit_system: Union[int, EclUnits.UnitSystem]
    ) -> ConvertUnits:
        """Creates a ConvertUnits object for unit conversions for water.

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
                CreateUnitConverter.ToSI.compressibility(unit_system),
                CreateUnitConverter.ToSI.recip_fvf_visc(unit_system),
                CreateUnitConverter.ToSI.compressibility(unit_system),
            ],
        )

    def create_water(self, raw: EclPropertyTableRawData, unit_system: int) -> None:
        """Creates interpolants for water from the given raw Eclipse data and uses
        a water unit converter based on the given unit system.

        Args:
            raw: Eclipse raw data object
            unit_system: Integer representation of the unit system used in Eclipse data

        """
        # Holding raw.num_tables values
        ret: List[PvxOBase] = []

        cvrt = self.water_unit_converter(unit_system)

        ret = self.make_interpolants_from_raw_data(
            raw,
            lambda table_index, raw: WaterImpl(
                table_index, raw, self.surface_mass_densities[table_index], cvrt
            ),
        )

        if len(self.surface_mass_densities) != len(ret):
            raise ValueError(
                (
                    "The given Eclipse INIT file seems to be broken"
                    "(number of surface density values does not equal number of PVT regions)."
                )
            )

        self._regions = ret

    @staticmethod
    def from_ecl_init_file(
        ecl_init_file: EclFile, keep_unit_system: bool = False
    ) -> Optional["Water"]:
        """Reads the given Eclipse file and creates a Water object from its data.

        Args:
            ecl_init_file: Eclipse INIT file
            keep_unit_system:
                Set to True if the unit system used in the Eclipse file
                shall be kept, False if SI shall be used.

        Returns:
            A Water object or None if the data in the Eclipse file was invalid

        """
        intehead = ecl_init_file.__getitem__(InitFileDefinitions.INTEHEAD_KW)
        intehead_phase = intehead[InitFileDefinitions.INTEHEAD_PHASE_INDEX]

        if (intehead_phase & (1 << 2)) == 0:
            return None

        raw = EclPropertyTableRawData()

        tab_dims = ecl_init_file.__getitem__("TABDIMS")
        tab = ecl_init_file.__getitem__("TAB")

        raw.num_primary = 1  # Single record per region
        raw.num_rows = 1  # Single record per region
        raw.num_cols = 5  # [ Pw, 1/B, Cw, 1/(B*mu), Cw - Cv ]
        raw.num_tables = tab_dims[InitFileDefinitions.TABDIMS_NTPVTW_ITEM]

        if raw.num_tables == 0:
            return None

        num_tab_elements = (
            raw.num_primary * raw.num_rows * raw.num_cols * raw.num_tables
        )
        start = tab_dims[InitFileDefinitions.TABDIMS_IBPVTW_OFFSET_ITEM] - 1
        raw.data = tab[start : start + num_tab_elements]

        surface_mass_densities = surface_mass_density(
            ecl_init_file, EclPhaseIndex.AQUA, keep_unit_system
        )

        return Water(
            raw,
            intehead[InitFileDefinitions.INTEHEAD_UNIT_INDEX],
            surface_mass_densities,
            keep_unit_system,
        )
