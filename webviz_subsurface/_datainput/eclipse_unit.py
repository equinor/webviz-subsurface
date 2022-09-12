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
#  Copyright (C) 2009-2012 SINTEF ICT, Applied Mathematics.
#
########################################

from enum import IntEnum
from typing import Callable, List

from .units import Prefix, Unit, UnitBase


class EclUnitEnum(IntEnum):
    """An enum for the different unit systems"""

    ECL_SI_UNITS = 0
    ECL_METRIC_UNITS = 1
    ECL_FIELD_UNITS = 2
    ECL_LAB_UNITS = 3
    ECL_PVT_M_UNITS = 4


def unit_system_name(unit_system: EclUnitEnum) -> str:
    """Returns a string representation of the given unit system enum.

    Args:
        unit_system: Representation of the unit system as an enum.

    Returns:
        A string representation of the given unit system. In case of
        an undefined unit system, returns "UNKNOWN".

    """
    if unit_system == EclUnitEnum.ECL_SI_UNITS:
        return "SI"
    if unit_system == EclUnitEnum.ECL_METRIC_UNITS:
        return "METRIC"
    if unit_system == EclUnitEnum.ECL_FIELD_UNITS:
        return "FIELD"
    if unit_system == EclUnitEnum.ECL_LAB_UNITS:
        return "LAB"
    if unit_system == EclUnitEnum.ECL_PVT_M_UNITS:
        return "PVT-M"
    return "UNKNOWN"


class UnitSystems:
    # pylint: disable=too-few-public-methods
    """Namespace for unit systems"""

    class SI:
        # pylint: disable=too-few-public-methods
        """Namespace for SI unit system"""

        Pressure = Unit.pascal
        Temperature = Unit.deg_kelvin
        TemperatureOffset = 0.0
        AbsoluteTemperature = Unit.deg_kelvin
        Length = Unit.meter
        Time = Unit.second
        Mass = Unit.kilogram
        Permeability = Unit.square(Unit.meter)
        Transmissibility = Unit.cubic(Unit.meter)
        LiquidSurfaceVolume = Unit.Base(Unit.cubic(Unit.meter), "Sm^3")
        GasSurfaceVolume = Unit.Base(Unit.cubic(Unit.meter), "Sm^3")
        ReservoirVolume = Unit.Base(Unit.cubic(Unit.meter), "Rm^3")
        GasDissolutionFactor = GasSurfaceVolume / LiquidSurfaceVolume
        OilDissolutionFactor = LiquidSurfaceVolume / GasSurfaceVolume
        Density = Unit.kilogram / Unit.cubic(Unit.meter)
        PolymerDensity = Unit.kilogram / Unit.cubic(Unit.meter)
        Salinity = Unit.kilogram / Unit.cubic(Unit.meter)
        Viscosity = Unit.pascal * Unit.second
        Timestep = Unit.second
        SurfaceTension = Unit.newton / Unit.meter
        Energy = Unit.joule

    class Metric:
        # pylint: disable=too-few-public-methods
        """Namespace for metric unit system"""

        Pressure = Unit.bar
        Temperature = Unit.deg_celsius
        TemperatureOffset = Unit.deg_celsius_offset
        AbsoluteTemperature = Unit.deg_celsius
        Length = Unit.meter
        Time = Unit.day
        Mass = Unit.kilogram
        Permeability = Prefix.milli * Unit.darcy
        Transmissibility = (
            Prefix.centi * Unit.poise * Unit.cubic(Unit.meter) / (Unit.day * Unit.bar)
        )
        LiquidSurfaceVolume = Unit.Base(Unit.cubic(Unit.meter), "Sm^3")
        GasSurfaceVolume = Unit.Base(Unit.cubic(Unit.meter), "Sm^3")
        ReservoirVolume = Unit.Base(Unit.cubic(Unit.meter), "Rm^3")
        GasDissolutionFactor = GasSurfaceVolume / LiquidSurfaceVolume
        OilDissolutionFactor = LiquidSurfaceVolume / GasSurfaceVolume
        Density = Unit.kilogram / Unit.cubic(Unit.meter)
        PolymerDensity = Unit.kilogram / Unit.cubic(Unit.meter)
        Salinity = Unit.kilogram / Unit.cubic(Unit.meter)
        Viscosity = Prefix.centi * Unit.poise
        Timestep = Unit.day
        SurfaceTension = Unit.dyne / (Prefix.centi * Unit.meter)
        Energy = Prefix.kilo * Unit.joule

    class Field:
        # pylint: disable=too-few-public-methods
        """Namespace for field unit system"""

        Pressure = Unit.psi
        Temperature = Unit.deg_fahrenheit
        TemperatureOffset = Unit.deg_fahrenheit_offset
        AbsoluteTemperature = Unit.deg_fahrenheit
        Length = Unit.feet
        Time = Unit.day
        Mass = Unit.pound
        Permeability = Prefix.milli * Unit.darcy
        Transmissibility = Prefix.centi * Unit.poise * Unit.stb / (Unit.day * Unit.psi)
        LiquidSurfaceVolume = Unit.Base(Unit.barrel, "rstb")
        GasSurfaceVolume = Unit.Base(Unit.cubic(Unit.feet), "scf")
        ReservoirVolume = Unit.Base(Unit.barrel, "RB")
        GasDissolutionFactor = GasSurfaceVolume / LiquidSurfaceVolume
        OilDissolutionFactor = LiquidSurfaceVolume / GasSurfaceVolume
        Density = Unit.pound / Unit.cubic(Unit.feet)
        PolymerDensity = Unit.pound / Unit.stb
        Salinity = Unit.pound / Unit.stb
        Viscosity = Prefix.centi * Unit.poise
        Timestep = Unit.day
        SurfaceTension = Unit.dyne / (Prefix.centi * Unit.meter)
        Energy = Unit.btu

    class Lab:
        # pylint: disable=too-few-public-methods
        """Namespace for lab unit system"""

        Pressure = Unit.atm
        Temperature = Unit.deg_celsius
        TemperatureOffset = Unit.deg_celsius_offset
        AbsoluteTemperature = Unit.deg_celsius
        Length = Prefix.centi * Unit.meter
        Time = Unit.hour
        Mass = Unit.gram
        Permeability = Prefix.milli * Unit.darcy
        Transmissibility = (
            Prefix.centi
            * Unit.poise
            * Unit.cubic(Prefix.centi * Unit.meter)
            / (Unit.hour * Unit.atm)
        )
        LiquidSurfaceVolume = Unit.Base(Unit.cubic(Prefix.centi * Unit.meter), "Scm^3")
        GasSurfaceVolume = Unit.Base(Unit.cubic(Prefix.centi * Unit.meter), "Scm^3")
        ReservoirVolume = Unit.Base(Unit.cubic(Prefix.centi * Unit.meter), "Rcm^3")
        GasDissolutionFactor = GasSurfaceVolume / LiquidSurfaceVolume
        OilDissolutionFactor = LiquidSurfaceVolume / GasSurfaceVolume
        Density = Unit.gram / Unit.cubic(Prefix.centi * Unit.meter)
        PolymerDensity = Unit.gram / Unit.cubic(Prefix.centi * Unit.meter)
        Salinity = Unit.gram / Unit.cubic(Prefix.centi * Unit.meter)
        Viscosity = Prefix.centi * Unit.poise
        Timestep = Unit.hour
        SurfaceTension = Unit.dyne / (Prefix.centi * Unit.meter)
        Energy = Unit.joule

    class PVTM:
        # pylint: disable=too-few-public-methods
        """Namespace for PVTM unit system"""

        Pressure = Unit.atm
        Temperature = Unit.deg_celsius
        TemperatureOffset = Unit.deg_celsius_offset
        AbsoluteTemperature = Unit.deg_celsius
        Length = Unit.meter
        Time = Unit.day
        Mass = Unit.kilogram
        Permeability = Prefix.milli * Unit.darcy
        Transmissibility = (
            Prefix.centi * Unit.poise * Unit.cubic(Unit.meter) / (Unit.day * Unit.atm)
        )
        LiquidSurfaceVolume = Unit.Base(Unit.cubic(Unit.meter), "Sm^3")
        GasSurfaceVolume = Unit.Base(Unit.cubic(Unit.meter), "Sm^3")
        ReservoirVolume = Unit.Base(Unit.cubic(Unit.meter), "Rm^3")
        GasDissolutionFactor = GasSurfaceVolume / LiquidSurfaceVolume
        OilDissolutionFactor = LiquidSurfaceVolume / GasSurfaceVolume
        Density = Unit.kilogram / Unit.cubic(Unit.meter)
        PolymerDensity = Unit.kilogram / Unit.cubic(Unit.meter)
        Salinity = Unit.kilogram / Unit.cubic(Unit.meter)
        Viscosity = Prefix.centi * Unit.poise
        Timestep = Unit.day
        SurfaceTension = Unit.dyne / (Prefix.centi * Unit.meter)
        Energy = Prefix.kilo * Unit.joule


class EclUnits:
    """Namespace for units used in Eclipse"""

    class UnitSystem:
        """Base interface class for Eclipse specific unit systems.

        Raises NotImplementedErrors when used directly.
        """

        @staticmethod
        def density() -> UnitBase:
            """
            Returns:
                The unit system's unit of density (e.g. 1 kg/m^3)
            """
            raise NotImplementedError("The base class cannot be called directly.")

        @staticmethod
        def depth() -> UnitBase:
            """
            Returns:
                The unit system's unit of depth (e.g. 1 m)
            """
            raise NotImplementedError("The base class cannot be called directly.")

        @staticmethod
        def pressure() -> UnitBase:
            """
            Returns:
                The unit system's unit of pressure (e.g. 1 Pa)
            """
            raise NotImplementedError("The base class cannot be called directly.")

        @staticmethod
        def reservoir_rate() -> UnitBase:
            """
            Returns:
                The unit system's unit of the reservoir rate (e.g. m^3/s)
            """
            raise NotImplementedError("The base class cannot be called directly.")

        @staticmethod
        def reservoir_volume() -> UnitBase:
            """
            Returns:
                The unit system's unit of reservoir volume (e.g. rm^3)
            """
            raise NotImplementedError("The base class cannot be called directly.")

        @staticmethod
        def surface_volume_gas() -> UnitBase:
            """
            Returns:
                The unit system's unit of the surface volume of gas (e.g. sm^3)
            """
            raise NotImplementedError("The base class cannot be called directly.")

        @staticmethod
        def surface_volume_liquid() -> UnitBase:
            """
            Returns:
                The unit system's unit of the surface volume of liquids (e.g. sm^3)
            """
            raise NotImplementedError("The base class cannot be called directly.")

        @staticmethod
        def time() -> UnitBase:
            """
            Returns:
                The unit system's unit of time (e.g. s)
            """
            raise NotImplementedError("The base class cannot be called directly.")

        @staticmethod
        def transmissibility() -> UnitBase:
            """
            Returns:
                The unit system's unit of transmissibility (e.g. m^3)
            """
            raise NotImplementedError("The base class cannot be called directly.")

        @staticmethod
        def viscosity() -> UnitBase:
            """
            Returns:
                The unit system's unit of viscosity (e.g. Pa*s)
            """
            raise NotImplementedError("The base class cannot be called directly.")

        def dissolved_gas_oil_ratio(self) -> UnitBase:
            """
            Returns:
                The unit system's unit of the dissolved gas to oil ratio (e.g. [-])
            """
            return self.surface_volume_gas() / self.surface_volume_liquid()

        def vaporised_oil_gas_ratio(self) -> UnitBase:
            """
            Returns:
                The unit system's unit of the vaporised oil to gas ratio (e.g. [-])
            """
            return self.surface_volume_liquid() / self.surface_volume_gas()

    class EclSIUnitSystem(UnitSystem):
        @staticmethod
        def density() -> UnitBase:
            return UnitSystems.SI.Density

        @staticmethod
        def depth() -> UnitBase:
            return UnitSystems.SI.Length

        @staticmethod
        def pressure() -> UnitBase:
            return UnitSystems.SI.Pressure

        @staticmethod
        def reservoir_rate() -> UnitBase:
            return UnitSystems.SI.ReservoirVolume / UnitSystems.SI.Time

        @staticmethod
        def reservoir_volume() -> UnitBase:
            return UnitSystems.SI.ReservoirVolume

        @staticmethod
        def surface_volume_gas() -> UnitBase:
            return UnitSystems.SI.GasSurfaceVolume

        @staticmethod
        def surface_volume_liquid() -> UnitBase:
            return UnitSystems.SI.LiquidSurfaceVolume

        @staticmethod
        def time() -> UnitBase:
            return UnitSystems.SI.Time

        @staticmethod
        def transmissibility() -> UnitBase:
            return UnitSystems.SI.Transmissibility

        @staticmethod
        def viscosity() -> UnitBase:
            return UnitSystems.SI.Viscosity

    class EclMetricUnitSystem(UnitSystem):
        @staticmethod
        def density() -> UnitBase:
            return UnitSystems.Metric.Density

        @staticmethod
        def depth() -> UnitBase:
            return UnitSystems.Metric.Length

        @staticmethod
        def pressure() -> UnitBase:
            return UnitSystems.Metric.Pressure

        @staticmethod
        def reservoir_rate() -> UnitBase:
            return UnitSystems.Metric.ReservoirVolume / UnitSystems.Metric.Time

        @staticmethod
        def reservoir_volume() -> UnitBase:
            return UnitSystems.Metric.ReservoirVolume

        @staticmethod
        def surface_volume_gas() -> UnitBase:
            return UnitSystems.Metric.GasSurfaceVolume

        @staticmethod
        def surface_volume_liquid() -> UnitBase:
            return UnitSystems.Metric.LiquidSurfaceVolume

        @staticmethod
        def time() -> UnitBase:
            return UnitSystems.Metric.Time

        @staticmethod
        def transmissibility() -> UnitBase:
            return UnitSystems.Metric.Transmissibility

        @staticmethod
        def viscosity() -> UnitBase:
            return UnitSystems.Metric.Viscosity

    class EclFieldUnitSystem(UnitSystem):
        @staticmethod
        def density() -> UnitBase:
            return UnitSystems.Field.Density

        @staticmethod
        def depth() -> UnitBase:
            return UnitSystems.Field.Length

        @staticmethod
        def pressure() -> UnitBase:
            return UnitSystems.Field.Pressure

        @staticmethod
        def reservoir_rate() -> UnitBase:
            return UnitSystems.Field.ReservoirVolume / UnitSystems.Field.Time

        @staticmethod
        def reservoir_volume() -> UnitBase:
            return UnitSystems.Field.ReservoirVolume

        @staticmethod
        def surface_volume_gas() -> UnitBase:
            return UnitSystems.Field.GasSurfaceVolume

        @staticmethod
        def surface_volume_liquid() -> UnitBase:
            return UnitSystems.Field.LiquidSurfaceVolume

        @staticmethod
        def time() -> UnitBase:
            return UnitSystems.Field.Time

        @staticmethod
        def transmissibility() -> UnitBase:
            return UnitSystems.Field.Transmissibility

        @staticmethod
        def viscosity() -> UnitBase:
            return UnitSystems.Field.Viscosity

    class EclLabUnitSystem(UnitSystem):
        @staticmethod
        def density() -> UnitBase:
            return UnitSystems.Lab.Density

        @staticmethod
        def depth() -> UnitBase:
            return UnitSystems.Lab.Length

        @staticmethod
        def pressure() -> UnitBase:
            return UnitSystems.Lab.Pressure

        @staticmethod
        def reservoir_rate() -> UnitBase:
            return UnitSystems.Lab.ReservoirVolume / UnitSystems.Lab.Time

        @staticmethod
        def reservoir_volume() -> UnitBase:
            return UnitSystems.Lab.ReservoirVolume

        @staticmethod
        def surface_volume_gas() -> UnitBase:
            return UnitSystems.Lab.GasSurfaceVolume

        @staticmethod
        def surface_volume_liquid() -> UnitBase:
            return UnitSystems.Lab.LiquidSurfaceVolume

        @staticmethod
        def time() -> UnitBase:
            return UnitSystems.Lab.Time

        @staticmethod
        def transmissibility() -> UnitBase:
            return UnitSystems.Lab.Transmissibility

        @staticmethod
        def viscosity() -> UnitBase:
            return UnitSystems.Lab.Viscosity

    class EclPvtMUnitSystem(UnitSystem):
        @staticmethod
        def density() -> UnitBase:
            return UnitSystems.PVTM.Density

        @staticmethod
        def depth() -> UnitBase:
            return UnitSystems.PVTM.Length

        @staticmethod
        def pressure() -> UnitBase:
            return UnitSystems.PVTM.Pressure

        @staticmethod
        def reservoir_rate() -> UnitBase:
            return UnitSystems.PVTM.ReservoirVolume / UnitSystems.PVTM.Time

        @staticmethod
        def reservoir_volume() -> UnitBase:
            return UnitSystems.PVTM.ReservoirVolume

        @staticmethod
        def surface_volume_gas() -> UnitBase:
            return UnitSystems.PVTM.GasSurfaceVolume

        @staticmethod
        def surface_volume_liquid() -> UnitBase:
            return UnitSystems.PVTM.LiquidSurfaceVolume

        @staticmethod
        def time() -> UnitBase:
            return UnitSystems.PVTM.Time

        @staticmethod
        def transmissibility() -> UnitBase:
            return UnitSystems.PVTM.Transmissibility

        @staticmethod
        def viscosity() -> UnitBase:
            return UnitSystems.PVTM.Viscosity

    @staticmethod
    def create_unit_system(unit_system: int) -> UnitSystem:
        if unit_system == EclUnitEnum.ECL_SI_UNITS:
            return EclUnits.EclSIUnitSystem()
        if unit_system == EclUnitEnum.ECL_METRIC_UNITS:
            return EclUnits.EclMetricUnitSystem()
        if unit_system == EclUnitEnum.ECL_FIELD_UNITS:
            return EclUnits.EclFieldUnitSystem()
        if unit_system == EclUnitEnum.ECL_LAB_UNITS:
            return EclUnits.EclLabUnitSystem()
        if unit_system == EclUnitEnum.ECL_PVT_M_UNITS:
            return EclUnits.EclPvtMUnitSystem()
        raise ValueError(f"Unsupported Unit Convention: {unit_system}")


class ConvertUnits:
    # pylint: disable=too-few-public-methods
    """A structure holding callables for unit conversions.

    Attributes:
        independent: Callable for unit conversion of independent variable.
        column: List of callables for unit conversion of each of the dependent variables.
    """

    def __init__(
        self,
        independent: Callable[
            [
                float,
            ],
            float,
        ],
        column: List[
            Callable[
                [
                    float,
                ],
                float,
            ]
        ],
    ) -> None:
        """Initiates an object holding conversion callables
        for each of the independent and dependent variables
        respectively.

        Args:
            independent: Callable for unit conversion of independent variable.
            column: List of callables for unit conversion of each of the dependent variables.
        """
        self.independent: Callable[
            [
                float,
            ],
            float,
        ] = independent
        self.column: List[
            Callable[
                [
                    float,
                ],
                float,
            ]
        ] = column


class CreateUnitConverter:
    """Namespace for methods creating unit converters"""

    @staticmethod
    # pylint: disable=invalid-name
    def create_converter_to_SI(
        uscale: float,
    ) -> Callable[[float,], float]:
        """Creates callable that converts a quantity from its measurement units to SI units.

        Example:
        quantity = 100 bar
        [quantity](METRIC) = bar
        [quantity](SI) = Pa
        uscale = METRIC.pressure() = 100 000 Pa/bar
        returns 100 bar * 100 000 Pa/bar = 10 000 000 Pa

        Args:
            uscale: Unit scale of the measurement unit system
                    (e.g. 100 000 Pa for unit system using bar as pressure unit)

        Returns:
            Callable that converts a quantity from its measurement unit system (given by uscale)
            to SI units.
        """
        return lambda quantity: Unit.Convert.from_(quantity, uscale)

    @staticmethod
    def rs_scale(unit_system: EclUnits.UnitSystem) -> float:
        # Rs = [sVolume(Gas) / sVolume(Liquid)]
        return (
            unit_system.surface_volume_gas().value
            / unit_system.surface_volume_liquid().value
        )

    @staticmethod
    def rv_scale(unit_system: EclUnits.UnitSystem) -> float:
        # Rv = [sVolume(Liq) / sVolume(Gas)]
        return (
            unit_system.surface_volume_liquid().value
            / unit_system.surface_volume_gas().value
        )

    @staticmethod
    def fvf_scale(unit_system: EclUnits.UnitSystem) -> float:
        # B = [rVolume / sVolume(Liquid)]
        return (
            unit_system.reservoir_volume().value
            / unit_system.surface_volume_liquid().value
        )

    @staticmethod
    def fvf_gas_scale(unit_system: EclUnits.UnitSystem) -> float:
        # B = [rVolume / sVolume(Gas)]
        return (
            unit_system.reservoir_volume().value
            / unit_system.surface_volume_gas().value
        )

    class ToSI:
        @staticmethod
        def fvf(
            unit_system: EclUnits.UnitSystem,
        ) -> Callable[[float,], float]:
            return CreateUnitConverter.create_converter_to_SI(
                CreateUnitConverter.fvf_scale(unit_system)
            )

        @staticmethod
        def density(
            unit_system: EclUnits.UnitSystem,
        ) -> Callable[[float,], float]:
            return CreateUnitConverter.create_converter_to_SI(
                unit_system.density().value
            )

        @staticmethod
        def pressure(
            unit_system: EclUnits.UnitSystem,
        ) -> Callable[[float,], float]:
            return CreateUnitConverter.create_converter_to_SI(
                unit_system.pressure().value
            )

        @staticmethod
        def compressibility(
            unit_system: EclUnits.UnitSystem,
        ) -> Callable[[float,], float]:
            return CreateUnitConverter.create_converter_to_SI(
                1.0 / unit_system.pressure().value
            )

        @staticmethod
        def viscosity(
            unit_system: EclUnits.UnitSystem,
        ) -> Callable[[float,], float]:
            return CreateUnitConverter.create_converter_to_SI(
                unit_system.viscosity().value
            )

        @staticmethod
        def dissolved_gas_oil_ratio(
            unit_system: EclUnits.UnitSystem,
        ) -> Callable[[float,], float]:
            return CreateUnitConverter.create_converter_to_SI(
                CreateUnitConverter.rs_scale(unit_system)
            )

        @staticmethod
        def vaporised_oil_gas_ratio(
            unit_system: EclUnits.UnitSystem,
        ) -> Callable[[float,], float]:
            return CreateUnitConverter.create_converter_to_SI(
                CreateUnitConverter.rv_scale(unit_system)
            )

        @staticmethod
        def recip_fvf(
            unit_system: EclUnits.UnitSystem,
        ) -> Callable[[float,], float]:
            return CreateUnitConverter.create_converter_to_SI(
                1.0 / CreateUnitConverter.fvf_scale(unit_system)
            )

        @staticmethod
        def recip_fvf_deriv_press(
            unit_system: EclUnits.UnitSystem,
        ) -> Callable[[float,], float]:
            # d(1/B)/dp
            b_scale = CreateUnitConverter.fvf_scale(unit_system)
            p_scale = unit_system.pressure().value

            return CreateUnitConverter.create_converter_to_SI(1.0 / (b_scale * p_scale))

        @staticmethod
        def recip_fvf_deriv_vap_oil(
            unit_system: EclUnits.UnitSystem,
        ) -> Callable[[float,], float]:
            # d(1/B)/dRv
            b_scale = CreateUnitConverter.fvf_scale(unit_system)
            rv_scale = CreateUnitConverter.rv_scale(unit_system)

            return CreateUnitConverter.create_converter_to_SI(
                1.0 / (b_scale * rv_scale)
            )

        @staticmethod
        def recip_fvf_visc(
            unit_system: EclUnits.UnitSystem,
        ) -> Callable[[float,], float]:
            b_scale = CreateUnitConverter.fvf_scale(unit_system)
            visc_scale = unit_system.viscosity().value

            return CreateUnitConverter.create_converter_to_SI(
                1.0 / (b_scale * visc_scale)
            )

        @staticmethod
        def recip_fvf_visc_deriv_press(
            unit_system: EclUnits.UnitSystem,
        ) -> Callable[[float,], float]:
            # d(1/(B*mu))/dp
            b_scale = CreateUnitConverter.fvf_scale(unit_system)
            p_scale = unit_system.pressure().value
            visc_scale = unit_system.viscosity().value

            return CreateUnitConverter.create_converter_to_SI(
                1.0 / (b_scale * visc_scale * p_scale)
            )

        @staticmethod
        def recip_fvf_visc_deriv_vap_oil(
            unit_system: EclUnits.UnitSystem,
        ) -> Callable[[float,], float]:
            # d(1/(B*mu))/dRv
            b_scale = CreateUnitConverter.fvf_scale(unit_system)
            visc_scale = unit_system.viscosity().value
            rv_scale = CreateUnitConverter.rv_scale(unit_system)

            return CreateUnitConverter.create_converter_to_SI(
                1.0 / (b_scale * visc_scale * rv_scale)
            )

        @staticmethod
        def recip_fvf_gas(
            unit_system: EclUnits.UnitSystem,
        ) -> Callable[[float,], float]:
            return CreateUnitConverter.create_converter_to_SI(
                1.0 / CreateUnitConverter.fvf_gas_scale(unit_system)
            )

        @staticmethod
        def recip_fvf_gas_deriv_press(
            unit_system: EclUnits.UnitSystem,
        ) -> Callable[[float,], float]:
            # d(1/B)/dp
            b_scale = CreateUnitConverter.fvf_gas_scale(unit_system)
            p_scale = unit_system.pressure().value

            return CreateUnitConverter.create_converter_to_SI(1.0 / (b_scale * p_scale))

        @staticmethod
        def recip_fvf_gas_deriv_vap_oil(
            unit_system: EclUnits.UnitSystem,
        ) -> Callable[[float,], float]:
            # d(1/B)/dRv
            b_scale = CreateUnitConverter.fvf_gas_scale(unit_system)
            rv_scale = CreateUnitConverter.rv_scale(unit_system)

            return CreateUnitConverter.create_converter_to_SI(
                1.0 / (b_scale * rv_scale)
            )

        @staticmethod
        def recip_fvf_gas_visc(
            unit_system: EclUnits.UnitSystem,
        ) -> Callable[[float,], float]:
            b_scale = CreateUnitConverter.fvf_gas_scale(unit_system)
            visc_scale = unit_system.viscosity().value

            return CreateUnitConverter.create_converter_to_SI(
                1.0 / (b_scale * visc_scale)
            )

        @staticmethod
        def recip_fvf_gas_visc_deriv_press(
            unit_system: EclUnits.UnitSystem,
        ) -> Callable[[float,], float]:
            # d(1/(B*mu))/dp
            b_scale = CreateUnitConverter.fvf_gas_scale(unit_system)
            p_scale = unit_system.pressure().value
            visc_scale = unit_system.viscosity().value

            return CreateUnitConverter.create_converter_to_SI(
                1.0 / (b_scale * visc_scale * p_scale)
            )

        @staticmethod
        def recip_fvf_gas_visc_deriv_vap_oil(
            unit_system: EclUnits.UnitSystem,
        ) -> Callable[[float,], float]:
            # d(1/(B*mu))/dRv
            b_scale = CreateUnitConverter.fvf_gas_scale(unit_system)
            visc_scale = unit_system.viscosity().value
            rv_scale = CreateUnitConverter.rv_scale(unit_system)

            return CreateUnitConverter.create_converter_to_SI(
                1.0 / (b_scale * visc_scale * rv_scale)
            )
