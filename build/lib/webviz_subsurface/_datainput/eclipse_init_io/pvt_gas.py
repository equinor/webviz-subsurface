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

from typing import Callable, Optional, Tuple, Union

import numpy as np

# opm is only available for Linux,
# hence, ignore any import exception here to make
# it still possible to use the PvtPlugin on
# machines with other OSes.
#
# NOTE: Functions in this file cannot be used
#       on non-Linux OSes.
try:
    from opm.io.ecl import EclFile
except ImportError:
    pass

from ..eclipse_unit import ConvertUnits, CreateUnitConverter, EclUnitEnum, EclUnits
from .pvt_common import (
    EclPhaseIndex,
    EclPropertyTableRawData,
    FluidImplementation,
    InitFileDefinitions,
    PVDx,
    PVTx,
    PvxOBase,
    surface_mass_density,
)


class WetGas(PvxOBase):
    """Class holding a PVT interpolant and access methods for PVT data for wet gas

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
        """Initializes a WetGas object.

        Creates an interpolant for wet gas for the Eclipse data given
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
        """Computes formation volume factor values
        for the given ratio and pressure values.

        Args:
            ratio: Ratio (key) values the volume factor values are requested for.
            pressure: Pressure values the volume factor values are requested for.

        Returns:
            Volume factor values for the given ratio and pressure values.

        """
        # Remember:
        # PKey   Inner   C0     C1         C2           C3
        # Pg     Rv      1/B    1/(B*mu)   d(1/B)/dRv   d(1/(B*mu))/dRv
        #        :       :      :          :            :
        return self.__interpolant.formation_volume_factor(pressure, ratio)

    def viscosity(self, ratio: np.ndarray, pressure: np.ndarray) -> np.ndarray:
        """Computes viscosity values for the given ratio and pressure values.

        Args:
            ratio: Ratio (key) values the viscosity values are requested for.
            pressure: Pressure values the viscosity values are requested for.

        Returns:
            Viscosity values for the given ratio and pressure values.

        """
        # Remember:
        # PKey   Inner   C0     C1         C2           C3
        # Pg     Rv      1/B    1/(B*mu)   d(1/B)/dRv   d(1/(B*mu))/dRv
        #        :       :      :          :            :
        return self.__interpolant.viscosity(pressure, ratio)

    def density(self, ratio: np.ndarray, pressure: np.ndarray) -> np.ndarray:
        """Args:
            ratio: Ratio (key) values the density values are requested for.
            pressure: Pressure values the density values are requested for.

        Returns:
            Density values for the given ratio and pressure values.

        """
        # rho_g = (rho_g,sc + Rv * rho_o,sc) / B_g
        fvf_gas = self.formation_volume_factor(ratio, pressure)
        return np.array(
            [
                (
                    self.__surface_mass_density_gas
                    + ratio_sample * self.__surface_mass_density_oil
                )
                / fvf_gas_sample
                for ratio_sample, fvf_gas_sample in zip(ratio, fvf_gas)
            ]
        )

    def get_keys(self) -> np.ndarray:
        """Returns all primary pressure values (Pg)"""
        return self.__interpolant.get_keys()

    def get_independents(self) -> np.ndarray:
        """Returns all gas ratio values (Rv)"""
        return self.__interpolant.get_independents()


class DryGas(PvxOBase):
    """Class holding a PVT interpolant and access methods for PVT data for dry gas

    Attributes:
        interpolant: The interpolant object
    """

    def __init__(
        self,
        table_index: int,
        raw: EclPropertyTableRawData,
        surface_mass_density_gas: float,
        convert: ConvertUnits,
    ) -> None:
        """Initializes a DryGas object.

        Creates an interpolant for dry gas for the Eclipse data given
        by the raw data in the table with the given index.

        Args:
            index_table: Index of the PVT table
            raw: Eclipse raw data object
            surface_mass_density_gas: Surface mass density of gas
            convert: ConvertUnits object for unit conversions

        """
        self.__interpolant = PVDx(table_index, raw, convert)
        self.__surface_mass_density_gas = surface_mass_density_gas

    def formation_volume_factor(
        self, ratio: np.ndarray, pressure: np.ndarray
    ) -> np.ndarray:
        """Computes formation volume factor values
        for the given pressure values.

        Args:
            ratio: Dummy argument, only to conform to interface of base class.
            pressure: Pressure values the volume factor values are requested for.

        Returns:
            Volume factor values for the given pressure values.

        """
        return self.__interpolant.formation_volume_factor(pressure)

    def viscosity(self, ratio: np.ndarray, pressure: np.ndarray) -> np.ndarray:
        """Computes viscosity values for the given pressure values.

        Args:
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
        # rho_g = rho_g,sc / B_g
        fvf_gas = self.formation_volume_factor(ratio, pressure)
        return np.array(
            [
                self.__surface_mass_density_gas / fvf_gas_sample
                for fvf_gas_sample in fvf_gas
            ]
        )

    def get_keys(self) -> np.ndarray:
        """Returns all primary keys.

        Since this is dry gas, there is no dependency on Rv.
        Hence, this method returns a list holding floats of value 0.0
        for each independent value.

        """
        return self.__interpolant.get_keys()

    def get_independents(self) -> np.ndarray:
        """Returns all independent pressure values (Pg)"""
        return self.__interpolant.get_independents()


class Gas(FluidImplementation):
    """Class for storing PVT tables for gas

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
        surface_mass_densities: Tuple[np.ndarray, np.ndarray],
        keep_unit_system: bool = False,
    ) -> None:
        """Initializes a Gas object.

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
        self.create_pvt_interpolants(raw, unit_system)

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
                rf"/{{{unit_system.surface_volume_gas().symbol}}}$"
            )
        return (
            f"{unit_system.reservoir_volume().symbol}"
            f"/{unit_system.surface_volume_gas().symbol}"
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
                rf"${{{unit_system.surface_volume_liquid().symbol}}}/"
                rf"{{{unit_system.surface_volume_gas().symbol}}}$"
            )
        return (
            f"{unit_system.surface_volume_liquid().symbol}/"
            f"{unit_system.surface_volume_gas().symbol}"
        )

    def create_pvt_interpolants(
        self, raw: EclPropertyTableRawData, unit_system: int
    ) -> None:
        """Creates interpolants for PVT data based on the type of the gas (i.e. dry or wet gas).

        Args:
            raw: Eclipse raw data object
            unit_system: Number describing the unit system the values in the raw data are stored in

        Raises:
            A FluidImplementation.InvalidArgument exception
            in case of a size mismatch in the raw data.

        """
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
            self.create_dry_gas(raw, unit_system)
        else:
            self.create_wet_gas(raw, unit_system)

    def dry_gas_unit_converter(
        self, unit_system: Union[int, EclUnits.UnitSystem]
    ) -> ConvertUnits:
        """Creates a ConvertUnits object for unit conversions for dry gas.

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
                CreateUnitConverter.ToSI.recip_fvf_gas(unit_system),
                CreateUnitConverter.ToSI.recip_fvf_gas_visc(unit_system),
                CreateUnitConverter.ToSI.recip_fvf_gas_deriv_press(unit_system),
                CreateUnitConverter.ToSI.recip_fvf_gas_visc_deriv_press(unit_system),
            ],
        )

    def wet_gas_unit_converter(
        self, unit_system: Union[int, EclUnits.UnitSystem]
    ) -> Tuple[Callable[[float,], float,], ConvertUnits]:
        """Creates a tuple consisting of a callable and a ConvertUnits object
        for unit conversions for wet gas.

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
            CreateUnitConverter.ToSI.pressure(unit_system),
            ConvertUnits(
                CreateUnitConverter.ToSI.vaporised_oil_gas_ratio(unit_system),
                [
                    CreateUnitConverter.ToSI.recip_fvf_gas(unit_system),
                    CreateUnitConverter.ToSI.recip_fvf_gas_visc(unit_system),
                    CreateUnitConverter.ToSI.recip_fvf_gas_deriv_vap_oil(unit_system),
                    CreateUnitConverter.ToSI.recip_fvf_gas_visc_deriv_vap_oil(
                        unit_system
                    ),
                ],
            ),
        )

    def create_dry_gas(self, raw: EclPropertyTableRawData, unit_system: int) -> None:
        """Creates interpolants for dry gas from the given raw Eclipse data and uses
        a dry gas unit converter based on the given unit system.

        Args:
            raw: Eclipse raw data object
            unit_system: Integer representation of the unit system used in Eclipse data

        """
        cvrt = self.dry_gas_unit_converter(unit_system)

        self._regions = self.make_interpolants_from_raw_data(
            # Inner   C0     C1         C2           C3
            # Pg      1/B    1/(B*mu)   d(1/B)/dRv   d(1/(B*mu))/dRv
            #         :       :         :            :
            raw,
            lambda table_index, raw: DryGas(
                table_index, raw, self.surface_mass_densities[1][table_index], cvrt
            ),
        )

    def create_wet_gas(self, raw: EclPropertyTableRawData, unit_system: int) -> None:
        """Creates interpolants for wet gas from the given raw Eclipse data and uses
        a wet gas unit converter based on the given unit system.

        Args:
            raw: Eclipse raw data object
            unit_system: Integer representation of the unit system used in Eclipse data

        """
        cvrt = self.wet_gas_unit_converter(unit_system)

        self._regions = self.make_interpolants_from_raw_data(
            # PKey   Inner   C0     C1         C2           C3
            # Pg     Rv      1/B    1/(B*mu)   d(1/B)/dRv   d(1/(B*mu))/dRv
            #        :       :      :          :            :
            raw,
            lambda table_index, raw: WetGas(
                table_index,
                raw,
                self.surface_mass_densities[0][table_index],
                self.surface_mass_densities[1][table_index],
                cvrt,
            ),
        )

    def is_wet_gas(self) -> bool:
        """Checks if this fluid is wet gas.

        Returns:
            True if wet gas, else False

        """
        if len(self._regions) > 0:
            return isinstance(self._regions[0], WetGas)
        return False

    def is_dry_gas(self) -> bool:
        """Checks if this fluid is dry gas.

        Returns:
            True if dry gas, else False

        """
        if len(self._regions) > 0:
            return isinstance(self._regions[0], DryGas)
        return False

    @staticmethod
    def from_ecl_init_file(
        ecl_init_file: EclFile, keep_unit_system: bool = True
    ) -> Optional["Gas"]:
        """Reads the given Eclipse file and creates a Gas object from its data.

        Args:
            ecl_init_file: Eclipse INIT file
            keep_unit_system:
                Set to True if the unit system used in the Eclipse file
                shall be kept, False if SI shall be used.

        Returns:
            A Gas object or None if the data in the Eclipse file was invalid

        """
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

        surface_mass_densities = (
            surface_mass_density(ecl_init_file, EclPhaseIndex.LIQUID, keep_unit_system),
            surface_mass_density(ecl_init_file, EclPhaseIndex.VAPOUR, keep_unit_system),
        )

        return Gas(
            raw,
            intehead[InitFileDefinitions.INTEHEAD_UNIT_INDEX],
            surface_mass_densities,
            keep_unit_system,
        )
