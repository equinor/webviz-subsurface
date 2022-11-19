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

import abc
import warnings
from enum import Enum
from typing import Any, Callable, List, Optional, Tuple, Union

import numpy as np
from scipy import interpolate

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

from ..eclipse_unit import ConvertUnits, EclUnitEnum, EclUnits
from ..units import Unit


class EclPropertyTableRawData:  # pylint: disable=too-few-public-methods
    """
    A structure for storing read
    INIT file data.
    """

    def __init__(self) -> None:
        self.data = np.zeros(0)
        self.primary_key: List[int] = []
        self.num_primary = 0
        self.num_rows = 0
        self.num_cols = 0
        self.num_tables = 0


class PvxOBase(abc.ABC):
    """A common base class for all fluids.

    Should be inherited by any new fluid in order to have
    a common interface.
    """

    @abc.abstractmethod
    def get_keys(self) -> np.ndarray:
        """Returns all primary keys.

        Base implementation, raises a NotImplementedError.
        """

    @abc.abstractmethod
    def get_independents(self) -> np.ndarray:
        """Returns all independents.

        Base implementation, raises a NotImplementedError.
        """

    @abc.abstractmethod
    def formation_volume_factor(
        self, ratio: np.ndarray, pressure: np.ndarray
    ) -> np.ndarray:
        """Args:
            ratio: Ratio (key) values the volume factor values are requested for.
            pressure: Pressure values the volume factor values are requested for.

        Returns:
            All volume factor values for the given ratio and pressure values.

        Base implementation, raises a NotImplementedError.
        """

    @abc.abstractmethod
    def viscosity(self, ratio: np.ndarray, pressure: np.ndarray) -> np.ndarray:
        """Args:
            ratio: Ratio (key) values the viscosity values are requested for.
            pressure: Pressure values the viscosity values are requested for.

        Returns:
            All viscosity values for the given ratio and pressure values.

        Base implementation, raises a NotImplementedError.
        """

    @abc.abstractmethod
    def density(self, ratio: np.ndarray, pressure: np.ndarray) -> np.ndarray:
        """Args:
            ratio: Ratio (key) values the density values are requested for.
            pressure: Pressure values the density values are requested for.

        Returns:
            All density values for the given ratio and pressure values.

        Base implementation, raises a NotImplementedError.
        """


class PVxx(abc.ABC):
    """A base class for PVDx and PVTx"""

    @abc.abstractmethod
    def get_keys(self) -> np.ndarray:
        """Returns:
            All primary keys.

        Base implementation, raises a NotImplementedError.
        """

    @abc.abstractmethod
    def get_independents(self) -> np.ndarray:
        """Returns:
            All independents.

        Base implementation, raises a NotImplementedError.
        """

    @staticmethod
    def entry_valid(x: float) -> bool:
        """Returns:
        True if the given value is valid, i.e. < 1.0e20, else False.
        """
        return abs(x) < 1.0e20


class PVDx(PVxx):
    """A base class for dead and dry gas/oil respectively.

    Attributes:
        x: The independent values.
        y: A two-dimensional numpy array holding the dependent values.
        interpolation: A scipy interp1d object for interpolating the dependent values.
        inter_extrapolation: An extrap1d object for inter- and extrapolating the dependent values.
    """

    def __init__(
        self,
        index_table: int,
        raw: EclPropertyTableRawData,
        convert: ConvertUnits,
    ) -> None:
        """Extracts all values of the table with the given index from raw, converts them according
        to the given convert object and stores them as numpy arrays, x and y respectively.

        Creates an interpolation and an extrapolation object utilising scipy's interp1d and based on
        it the custom tailored extrap1d.

        Raises a ValueError if there is no interpolation interval given, that is when there are
        fewer than two independents.

        Args:
            index_table: The index of the table which values are supposed to be extracted.
            raw:
                An EclPropertyTableRawData object that was initialised based on an Eclipse
                INIT file.
            convert: A ConvertUnit object that contains callables for converting units.

        """
        self.x: np.ndarray = np.zeros(0)
        self.y: np.ndarray = np.zeros((raw.num_cols - 1, 0))

        column_stride = raw.num_rows * raw.num_tables * raw.num_primary
        table_stride = raw.num_primary * raw.num_rows

        for index_primary in range(0, raw.num_primary):
            if self.entry_valid(raw.primary_key[index_primary]):
                for index_row in range(0, raw.num_rows):
                    current_stride = (
                        index_table * table_stride
                        + index_primary * raw.num_rows
                        + index_row
                    )

                    if self.entry_valid(raw.data[column_stride * 0 + current_stride]):
                        self.x = np.append(
                            self.x,
                            convert.independent(
                                raw.data[column_stride * 0 + current_stride]
                            ),
                        )

                        self.y = np.append(
                            self.y,
                            [
                                [
                                    convert.column[index_column - 1](
                                        raw.data[
                                            column_stride * index_column
                                            + current_stride
                                        ]
                                    )
                                ]
                                for index_column in range(1, raw.num_cols)
                            ],
                            axis=1,
                        )

                    else:
                        break
            else:
                break

        if len(self.x) < 2:
            raise ValueError("No interpolation interval of non-zero size.")

        self.__interpolation = interpolate.interp1d(self.x, self.y, axis=1)

    def get_keys(self) -> np.ndarray:
        """Returns all primary keys.

        Since this is dry/dead gas/oil, there is no dependency on Rv/Rs.
        Hence, this method returns a list holding floats of value 0.0
        for each independent value.

        """
        return np.zeros(len(self.x))

    def get_independents(self) -> np.ndarray:
        """Returns all independents.

        In case of gas/oil this returns pressure values.

        """
        return self.x

    def formation_volume_factor(self, pressure: np.ndarray) -> np.ndarray:
        """Computes all formation volume factor values
        for the given pressure values.

        Args:
            pressure: Pressure values the volume factors are requested for.

        Returns:
            All formation volume factor values corresponding
            to the given pressure values.

        """
        # 1 / (1 / B)
        return self.__compute_quantity(pressure, lambda p: 1.0 / self.__fvf_recip(p))

    def viscosity(self, pressure: np.ndarray) -> np.ndarray:
        """Computes all viscosity values for the given pressure values.

        Args:
            pressure: Pressure values the viscosity values are requested for.

        Returns:
            All viscosity values corresponding
            to the given of pressure values.

        """
        # (1 / B) / (1 / (B * mu)
        return self.__compute_quantity(
            pressure, lambda p: self.__fvf_recip(p) / self.__fvf_mu_recip(p)
        )

    @staticmethod
    def __compute_quantity(
        pressures: np.ndarray, evaluate: Callable[[Any], Any]
    ) -> np.ndarray:
        """Calls the given evaluate function with each of the
        given pressure values and returns the results.

        Args:
            pressures: Pressure values
            evaluate: Evaluation function

        Returns:
            Values resulting from evaluating the pressure values.

        """
        result = np.zeros(len(pressures))

        for i, pressure in enumerate(pressures):
            result[i] = float(evaluate(pressure))

        return result

    def __fvf_recip(self, point: float) -> float:
        """Computes (possibly inter-/extrapolates) the reciprocal of
        the formation volume factor for the given point.

        Args:
            point:
                The pressure point the formation volume factor
                is requested for.

        Returns:
            The requested reciprocal formation volume factor.

        """
        return float(self.__interpolation(point)[0])

    def __fvf_mu_recip(self, point: float) -> float:
        """Computes (possibly inter-/extrapolates) the reciprocal of
        the product of the formation volume factor and viscosity
        for the given point.

        Args:
            point:
                The pressure point the formation volume factor
                is requested for.

        Returns:
            The requested reciprocal product of the formation volume factor
            and the viscosity.

        """
        return float(self.__interpolation(point)[1])


class PVTx(PVxx):
    def __init__(
        self,
        index_table: int,
        raw: EclPropertyTableRawData,
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
        """Extracts all values of the table with the given index from raw, converts them according
        to the given convert object and stores them as numpy arrays, keys, x and y respectively.

        Creates an interpolation and an extrapolation object utilising scipy's interp2d.

        Args:
            index_table: The index of the table which values are supposed to be extracted.
            raw:
                An EclPropertyTableRawData object that was initialised based on an Eclipse
                INIT file.
            convert:
                A tuple consisting of a callable for converting the primary keys and a
                ConvertUnit object that contains callables for converting units.

        """
        self.keys: np.ndarray = np.zeros(0)
        self.x: np.ndarray = np.zeros(0)
        self.y: List[np.ndarray] = [np.zeros(0) for _ in range(1, raw.num_cols)]

        column_stride = raw.num_rows * raw.num_tables * raw.num_primary
        table_stride = raw.num_primary * raw.num_rows

        for index_primary in range(0, raw.num_primary):
            if self.entry_valid(raw.primary_key[index_primary]):
                for index_row in range(0, raw.num_rows):
                    current_stride = (
                        index_table * table_stride
                        + index_primary * raw.num_rows
                        + index_row
                    )

                    if self.entry_valid(raw.data[column_stride * 0 + current_stride]):
                        self.keys = np.append(
                            self.keys, convert[0](raw.primary_key[index_primary])
                        )
                        self.x = np.append(
                            self.x,
                            convert[1].independent(
                                raw.data[column_stride * 0 + current_stride]
                            ),
                        )

                        for index_column in range(1, raw.num_cols):
                            self.y[index_column - 1] = np.append(
                                self.y[index_column - 1],
                                convert[1].column[index_column - 1](
                                    raw.data[
                                        column_stride * index_column + current_stride
                                    ]
                                ),
                            )

                    else:
                        break
            else:
                break

        # NOTE: If there is only one primary key, interp2d cannot be used.
        # As a fallback, use interp1d and make sure that the primary key asked for in
        # any of the methods of this instance is the one stored in self.keys[0].
        # Extrapolation is not possible.

        self.__single_key = np.amax(self.keys) == np.amin(self.keys)

        if len(self.x) < 2:
            raise ValueError("No interpolation interval of non-zero size.")

        # Ignore warnings here for now since this seems to be a bug in scipy
        # see: https://github.com/scipy/scipy/issues/4138
        # TODO: check if the warning can be fixed.

        warnings.filterwarnings("ignore")

        self.__interpolants: List[Union[interpolate.interp2d, interpolate.interp1d]] = [
            (
                interpolate.interp1d(self.x, self.y[index_column])
                if self.__single_key
                else interpolate.interp2d(
                    x=self.keys, y=self.x, z=self.y[index_column], kind="linear"
                )
            )
            for index_column in range(raw.num_cols - 1)
        ]

        warnings.filterwarnings("default")

    def get_keys(self) -> np.ndarray:
        """Returns all primary keys."""
        return self.keys

    def get_independents(self) -> np.ndarray:
        """Returns all independents."""
        return self.x

    def key_valid(self, key: np.ndarray) -> None:
        if self.__single_key and not all(k == self.keys[0] for k in key):
            raise ValueError(
                "Impossible to perform requested inter-/extrapolation due to insufficient data."
            )

    def formation_volume_factor(self, key: np.ndarray, x: np.ndarray) -> np.ndarray:
        """Computes formation volume factor values
        for the given ratio and pressure values.

        Args:
            key: Primary key values the volume factors are requested for.
            x: Independents the volume factors are requested for.

        Returns:
            Formation volume factor values corresponding
            to the given primary key and independent values.

        Base implementation, raises a NotImplementedError.

        """

        self.key_valid(key)

        return self.__compute_quantity(
            key,
            x,
            lambda curve, point: self.__interpolants[0](point)
            if self.__single_key
            else self.__interpolants[0](curve, point),
            lambda recip_fvf: 1.0 / recip_fvf,
        )

    def viscosity(self, key: np.ndarray, x: np.ndarray) -> np.ndarray:
        """Computes viscosity values for the given ratio and pressure values.

        Args:
            key: Primary key values the viscosity values are requested for.
            x: Independents the viscosity values are requested for.

        Returns:
            Viscosity values corresponding
            to the given primary key and independent values.

        Base implementation, raises a NotImplementedError.

        """

        self.key_valid(key)

        return self.__compute_quantity(
            key,
            x,
            lambda curve, point: [
                self.__interpolants[0](point),
                self.__interpolants[1](point),
            ]
            if self.__single_key
            else [
                self.__interpolants[0](curve, point),
                self.__interpolants[1](curve, point),
            ],
            lambda dense_vector: dense_vector[0] / dense_vector[1],
        )

    @staticmethod
    def __compute_quantity(
        key: np.ndarray,
        x: np.ndarray,
        inner_function: Callable,
        outer_function: Callable,
    ) -> np.ndarray:
        """Calls the evaluate method with each of the values
        in the given primary keys and the given inner_function
        and returns the results after the outer_function
        has been applied on each them.

        Args:
            key: Primary key values the viscosity values are requested for.
            x: Independents the viscosity values are requested for.
            inner_function: Callable for extracting a dense vector.
            outer_function:
                Callable that uses the dense vector to compute
                the requested quantity.

        Returns:
            Result values

        """

        num_vals = len(key)
        results = np.zeros(num_vals)
        if len(x) != num_vals:
            raise ValueError(
                "Number of inner sampling points does not match number of outer sampling points."
            )

        for i in range(0, num_vals):
            quantity = inner_function(key[i], x[i])

            results[i] = float(outer_function(quantity))

        return results


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
    TABDIMS_NTPVTW_ITEM = 12
    TABDIMS_IBPVTG_OFFSET_ITEM = 13
    TABDIMS_JBPVTG_OFFSET_ITEM = 14
    TABDIMS_NRPVTG_ITEM = 15
    TABDIMS_NPPVTG_ITEM = 16
    TABDIMS_NTPVTG_ITEM = 17
    LOGIHEAD_CONSTANT_OILCOMPR_INDEX = 39 - 1

    TABDIMS_IBDENS_OFFSET_ITEM = 18
    TABDIMS_NTDENS_ITEM = 19


class EclPhaseIndex(Enum):
    """Enumerator holding the different phases according
    to Eclipse file conventions"""

    AQUA = 0
    LIQUID = 1
    VAPOUR = 2


def is_const_compr_index() -> int:
    """Convenient function for better readibility.

    Returns:
        An integer that states that the oil has constant compression
        according to Eclipse LOGIHEAD file conventions.
    """
    return InitFileDefinitions.LOGIHEAD_CONSTANT_OILCOMPR_INDEX


def surface_mass_density(
    ecl_file: EclFile, phase: EclPhaseIndex, keep_unit_system: bool = True
) -> np.ndarray:
    """Extracts the surface mass density from the given Eclipse file for the given phase.

    Args:
        ecl_file: The Eclipse file to extract data from
        phase: Fluid phase to extract data for

    Returns:
        Surface mass density values.

    """
    if phase is EclPhaseIndex.LIQUID:
        col = 0
    elif phase is EclPhaseIndex.AQUA:
        col = 1
    elif phase is EclPhaseIndex.VAPOUR:
        col = 2
    else:
        raise AttributeError("Phase must be Liquid, Water or Vapour.")

    tabdims = ecl_file.__getitem__("TABDIMS")
    tab = ecl_file.__getitem__("TAB")

    start = tabdims[InitFileDefinitions.TABDIMS_IBDENS_OFFSET_ITEM] - 1
    nreg = tabdims[InitFileDefinitions.TABDIMS_NTDENS_ITEM]

    rho = tab[start + nreg * (col + 0) : start + nreg * (col + 1)]

    intehead = ecl_file.__getitem__(InitFileDefinitions.INTEHEAD_KW)
    unit_system = EclUnits.create_unit_system(
        intehead[InitFileDefinitions.INTEHEAD_UNIT_INDEX]
    )

    if not keep_unit_system:
        rho = [Unit.Convert.from_(rho_i, unit_system.density().value) for rho_i in rho]

    return rho


class FluidImplementation(abc.ABC):
    """Base class for fluid implementations

    Holds a list of regions (one per PVT table).

    Attributes:
        keep_unit_system: True if the original unit system was kept
        original_unit_system: An ErtEclUnitEnum representing the original unit system
    """

    class InvalidArgument(Exception):
        """An exception for invalid arguments"""

        def __init__(self, message: str):
            self.message = message
            super().__init__(message)

    class InvalidType(Exception):
        """An exception for invalid types"""

        def __init__(self) -> None:
            super().__init__("Invalid type. Only live oil/wet gas/water supported.")

    def __init__(self, unit_system: int, keep_unit_system: bool = True) -> None:
        """Initializes a fluid object.

        Args:
            unit_system: The original unit system
            keep_unit_system:
                True if the original unit system shall be kept,
                False if units shall be converted to SI units.

        """
        self._regions: List[PvxOBase] = []
        self.keep_unit_system = keep_unit_system
        self.original_unit_system = unit_system

    def pvdx_unit_converter(self) -> Optional[ConvertUnits]:
        """Creates a pseudo ConvertUnits object for PVDx interpolants
        that keeps the old unit system.

        Returns:
            Pseudo ConvertUnits object that does not do any unit conversions.

        """
        if self.keep_unit_system:
            return ConvertUnits(
                lambda x: x,
                [
                    lambda x: x,
                    lambda x: x,
                    lambda x: x,
                    lambda x: x,
                ],
            )
        return None

    def pvtx_unit_converter(
        self,
    ) -> Optional[Tuple[Callable[[float,], float,], ConvertUnits]]:
        """Creates a tuple consisting of a callable and a pseudo ConvertUnits
        object for PVTx interpolants which both keep the old unit system.

        Returns:
            Tuple of callable and pseudo ConvertUnits object
            which do not do any unit conversions.

        """
        if self.keep_unit_system:
            return (
                lambda x: x,
                ConvertUnits(
                    lambda x: x,
                    [
                        lambda x: x,
                        lambda x: x,
                        lambda x: x,
                        lambda x: x,
                    ],
                ),
            )
        return None

    @staticmethod
    def make_interpolants_from_raw_data(
        raw: EclPropertyTableRawData,
        construct: Callable[[int, EclPropertyTableRawData], PvxOBase],
    ) -> List[PvxOBase]:
        """Creates a list of interpolants from raw Eclipse table data using
        the given construct callable.

        Args:
            raw: Raw Eclipse table data to create interpolants from
            construct: Callable to use when creating interpolants

        Returns:
            A list of created interpolants.
        """
        interpolants: List[PvxOBase] = []

        for table_index in range(0, raw.num_tables):
            interpolants.append(construct(table_index, raw))

        return interpolants

    def pressure_unit(self, latex: bool = False) -> str:
        """Args:
            latex: True if the unit symbol shall be returned as Latex, False if not.

        Returns:
            A string containing the unit symbol of pressure.

        """
        unit_system = EclUnits.create_unit_system(
            self.original_unit_system
            if self.keep_unit_system
            else EclUnitEnum.ECL_SI_UNITS
        )

        if latex:
            return rf"${unit_system.pressure().symbol}$"
        return f"{unit_system.pressure().symbol}"

    def formation_volume_factor(
        self, region_index: int, ratio: np.ndarray, pressure: np.ndarray
    ) -> np.ndarray:
        """Args:
            region_index: Index of the requested PVT region
            ratio: Ratio values the data is requested for
            pressure: Pressure values the data is requested for

        Returns:
            Formation volume factor values according to the given values.

        """
        self.validate_region_index(region_index)

        return self._regions[region_index].formation_volume_factor(ratio, pressure)

    @abc.abstractmethod
    def formation_volume_factor_unit(self, latex: bool = False) -> str:
        """Args:
            latex: True if the unit symbol shall be returned as LaTeX, False if not.

        Returns:
            The unit symbol of the formation volume factor.

        Raises a NotImplementedError when called on a base class object.

        """

    def viscosity(
        self, region_index: int, ratio: np.ndarray, pressure: np.ndarray
    ) -> np.ndarray:
        """Args:
            region_index: Index of the requested PVT region
            ratio: Ratio values the data is requested for
            pressure: Pressure values the data is requested for

        Returns:
            Viscosity values according to the given values.

        """
        self.validate_region_index(region_index)

        return self._regions[region_index].viscosity(ratio, pressure)

    def viscosity_unit(self, latex: bool = False) -> str:
        """Creates and returns the unit symbol of the viscosity.

        Args:
            latex: True if the unit symbol shall be returned as LaTeX, False if not.

        Returns:
            The unit symbol of the viscosity.

        """
        unit_system = EclUnits.create_unit_system(
            self.original_unit_system
            if self.keep_unit_system
            else EclUnitEnum.ECL_SI_UNITS
        )

        if latex:
            return rf"${unit_system.viscosity().symbol}$"
        return unit_system.viscosity().symbol

    def density(
        self, region_index: int, ratio: np.ndarray, pressure: np.ndarray
    ) -> np.ndarray:
        """Args:
            region_index: Index of the requested PVT region
            ratio: Ratio values the data is requested for
            pressure: Pressure values the data is requested for

        Returns:
            Density values according to the given values.

        """
        self.validate_region_index(region_index)

        return self._regions[region_index].density(ratio, pressure)

    def density_unit(self, latex: bool = False) -> str:
        """Args:
            latex: True if the unit symbol shall be returned as LaTeX, False if not.

        Returns:
            The unit symbol of the density.

        """
        unit_system = EclUnits.create_unit_system(
            self.original_unit_system
            if self.keep_unit_system
            else EclUnitEnum.ECL_SI_UNITS
        )

        if latex:
            return rf"${unit_system.density().symbol}$"
        return unit_system.density().symbol

    @abc.abstractmethod
    def ratio_unit(self, latex: bool = False) -> str:
        """Args:
            latex: True if the unit symbol shall be returned as LaTeX, False if not.

        Returns:
            A string containing the unit symbol of the phase ratio (e.g. Sm³/Sm³).

        Raises a NotImplementedError when called on a base class object.

        """

    def get_region(self, region_index: int) -> PvxOBase:
        """Validates and returns the region at the given region_index.

        Args:
            region_index: Index of the requested PVT region

        Returns:
            The fluid interpolant related to the given region index.

        """
        self.validate_region_index(region_index)

        return self._regions[region_index]

    def validate_region_index(self, region_index: int) -> None:
        """Validates the given region index by ensuring that it is not out of range.

        Args:
            region_index: Index of the region to validate

        Raises:
            TypeError if the region is invalid.

        """
        if region_index >= len(self.regions()):
            if len(self.regions()) == 0:
                raise TypeError(
                    f"No oil PVT interpolant available in region {region_index + 1}."
                )

            raise TypeError(
                f"Region index {region_index + 1} outside valid range 0"
                f", ..., {len(self._regions) - 1}."
            )

    def regions(self) -> List[PvxOBase]:
        """Returns:
        All interpolants (one interpolant per region)

        """
        return self._regions

    def range_ratio(self, region_index: int) -> Tuple[float, float]:
        """Gets the primary key (ratio) range of the PVT region with the given index.

        Args:
            region_index: Index of the requested PVT region

        Returns:
            A tuple containing the min and max primary key (ratio) values.

        """
        region = self.get_region(region_index)
        return (min(region.get_keys()), max(region.get_keys()))

    def range_independent(self, region_index: int) -> Tuple[float, float]:
        """Gets the independent variable range of the PVT region with the given index.

        Args:
            region_index: Index of the requested PVT region

        Returns:
            A tuple containing the min and max independent values.

        """
        region = self.get_region(region_index)
        return (min(region.get_independents()), max(region.get_independents()))
