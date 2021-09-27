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

import re
from typing import Any, Dict, Union


class UnitBase:
    """This is a pseudo-base-class necessary due to class Prefix requiring
    a class type for operator type definitions.

    TODO (RMT): Can be removed as soon as 'from __future__ import annotations'
    is available (Python >= 3.7).
    """

    def __init__(self, value: float, symbol: str) -> None:
        raise NotImplementedError("This pseudo-class must not be used directly.")

    @property
    def value(self) -> float:
        raise NotImplementedError("This pseudo-class must not be used directly.")

    @property
    def raw_symbol(self) -> str:
        raise NotImplementedError("This pseudo-class must not be used directly.")

    @property
    def symbol(self) -> str:
        raise NotImplementedError("This pseudo-class must not be used directly.")

    def __mul__(self, other: Any) -> Any:
        raise NotImplementedError("This pseudo-class must not be used directly.")

    def __truediv__(self, other: Any) -> Any:
        raise NotImplementedError("This pseudo-class must not be used directly.")


# pylint: disable=too-few-public-methods
class Prefix:
    """Namespace for unit prefixes.

    Attributes:
        micro
        milli
        centi
        deci
        kilo
        mega
        giga
    """

    class Base:
        """Holds prefix factor and symbol of a Prefix and allows multiplication with Units.

        Raises NotImplementedErrors for other operations.

        Attributes:
            factor: The prefix factor (e.g. for kilo: 1.0e3)
            symbol: The prefix symbol (e.g. for kilo: k)
        """

        def __init__(self, factor: float, symbol: str) -> None:
            """Initializes a Prefix with the given factor and symbol.

            Args:
                factor: The prefix factor (e.g. for kilo: 1.0e3)
                symbol: The prefix symbol (e.g. for kilo: k)

            """
            self.factor = factor
            self.symbol = symbol

        def __mul__(self, unit: UnitBase) -> UnitBase:  # type: ignore[no-untyped-def]
            """Applies this factor to the given unit and returns the result as a new unit.

            Does also create a new symbol.

            Args:
                unit: The unit this prefix shall be applied on.

            Returns:
                A new unit as a result of the application of this prefix.

            """
            if issubclass(unit.__class__, UnitBase):
                return unit.__class__(
                    self.factor * unit.value, f"{self.symbol}{unit.symbol}"
                )

            raise TypeError("Can only be multiplied with a Unit.")

        def __add__(self, other):  # type: ignore[no-untyped-def]
            raise NotImplementedError("Prefixes can only be multiplied with a Unit.")

        def __sub__(self, other):  # type: ignore[no-untyped-def]
            raise NotImplementedError("Prefixes can only be multiplied with a Unit.")

        def __truediv__(self, other):  # type: ignore[no-untyped-def]
            raise NotImplementedError("Prefixes can only be multiplied with a Unit.")

    micro = Base(1.0e-6, "\u00B5")
    milli = Base(1.0e-3, "m")
    centi = Base(1.0e-2, "c")
    deci = Base(1.0e-1, "d")
    kilo = Base(1.0e3, "k")
    mega = Base(1.0e6, "M")
    giga = Base(1.0e9, "G")


class Unit:
    """Namespace for units"""

    class Base(UnitBase):
        """Common class for all units.

        Used to have one object holding both value and symbol of the unit.
        Does also allow multiplication and division with other units and takes
        care of keeping its symbol tidy.
        """

        # pylint: disable=super-init-not-called
        def __init__(
            self,
            value: Union[float, UnitBase],  # type: ignore[name-defined]
            symbol: str,
        ) -> None:
            """Creates a new unit instance.

            Tidies the given symbol.

            Args:
                value: Either a value or another unit
                symbol: The symbol of the unit

            Returns:
                A new unit with the given value and a tidy symbol.

            """
            if isinstance(value, float):
                self.__value = value
            else:
                self.__value = value.value

            self.__symbol = symbol

            self.__tidy_symbol()

        @property
        def value(self) -> float:
            """
            Returns:
                The value of the unit.

            """
            return self.__value

        @property
        def raw_symbol(self) -> str:
            """
            Returns:
                The raw symbol of the unit.

            """
            return self.__symbol

        @property
        def symbol(self) -> str:
            """
            Returns:
                The formatted symbol of the unit.

            """
            return self.__formatted_symbol()

        def __formatted_symbol(self) -> str:
            powers = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
            symbol = self.__symbol.replace("^", "").translate(powers)
            symbol = re.sub(r"\(([^*+\-\/]+)\)", r"\1", symbol)
            return symbol

        def __tidy_symbol(self) -> None:
            # pylint: disable=too-many-branches
            # pylint: disable=too-many-statements
            def add_symbol(
                current_symbol: str,
                current_power: str,
                in_denominator: bool,
                numerator: Dict[str, int],
                denominator: Dict[str, int],
            ) -> None:
                if current_symbol != "":
                    if not in_denominator:
                        if current_symbol not in numerator:
                            numerator[current_symbol] = 0
                        numerator[current_symbol] += int(
                            current_power if current_power != "" else 1
                        )
                    else:
                        if current_symbol not in denominator:
                            denominator[current_symbol] = 0
                        denominator[current_symbol] += int(
                            current_power if current_power != "" else 1
                        )

            self.__symbol = "".join(self.__symbol.split())
            numerator: Dict[str, int] = {}
            denominator: Dict[str, int] = {}

            in_parantheses = False
            in_denominator = False
            power = False
            current_power = ""
            current_symbol = ""

            for i, char in enumerate(self.__symbol):
                if char in ["*", "/", "(", ")"]:
                    add_symbol(
                        current_symbol,
                        current_power,
                        in_denominator,
                        numerator,
                        denominator,
                    )

                if char in ["*", "/", "(", ")"]:
                    if char == "*":
                        if not in_parantheses:
                            in_denominator = False
                    elif char == "/":
                        in_denominator = True
                    elif char == "(":
                        in_parantheses = True
                    elif char == ")":
                        in_parantheses = False

                    current_symbol = ""
                    current_power = ""
                    power = False
                elif char == "^":
                    power = True
                else:
                    if power:
                        current_power += char
                    else:
                        current_symbol += char

                if i == len(self.__symbol) - 1:
                    add_symbol(
                        current_symbol,
                        current_power,
                        in_denominator,
                        numerator,
                        denominator,
                    )

            self.__symbol = ""

            for num, num_power in numerator.items():
                for denom, denom_power in denominator.items():
                    if num == denom:
                        denominator[num] = max(0, denom_power - num_power)
                        num_power = max(0, num_power - denom_power)
                        break

                if num_power > 0:
                    if self.__symbol == "":
                        self.__symbol += num
                    else:
                        self.__symbol += f"*{num}"
                    if num_power > 1:
                        self.__symbol += f"^{num_power}"

            if len(denominator) > 0:
                self.__symbol += "/("

                for denom, denom_power in denominator.items():
                    if denom_power > 0:
                        if self.__symbol[-1] == "(":
                            self.__symbol += denom
                        else:
                            self.__symbol += f"*{denom}"
                        if denom_power > 1:
                            self.__symbol += f"^{denom_power}"

                self.__symbol += ")"

        def __mul__(
            self,
            other: Union[UnitBase, Prefix.Base, float, int],
        ) -> UnitBase:
            """Multiplies this unit with the given unit/float/int and
            returns the result as a new unit.

            Does also create a new symbol.

            Args:
                unit: The unit/float/int to multiply with.

            Returns:
                A new unit as a result of the operation.

            """
            if issubclass(other.__class__, UnitBase):
                return self.__class__(
                    self.value * other.value, f"{self.raw_symbol}*{other.raw_symbol}"
                )
            if isinstance(other, float):
                return self.__class__(self.value * other, self.raw_symbol)
            if isinstance(other, int):
                return self.__class__(self.value * float(other), self.raw_symbol)

            raise TypeError(
                "You can only multiply this unit with another unit, a float or an integer."
            )

        def __truediv__(
            self,
            other: Union[UnitBase, Prefix.Base, float, int],
        ) -> UnitBase:
            """Divides this unit by the given unit/float/int and returns the result as a new unit.

            Does also create a new symbol.

            Args:
                unit: The unit/float/int to divide by.

            Returns:
                A new unit as a result of the operation.

            """
            if issubclass(other.__class__, UnitBase):
                return self.__class__(
                    self.value / other.value, f"{self.raw_symbol}/({other.raw_symbol})"
                )
            if isinstance(other, float):
                return self.__class__(self.value / other, self.raw_symbol)
            if isinstance(other, int):
                return self.__class__(self.value / float(other), self.raw_symbol)

            raise TypeError(
                "You can only divide this unit by another unit, a float or an integer."
            )

    # Common powers
    @staticmethod
    def square(unit: UnitBase) -> UnitBase:
        """Computes the square product of the given unit.

        Args:
            unit: The unit the square product shall be computed for.

        Returns:
            A new unit holding the square product of the given unit.

        """
        return unit * unit

    @staticmethod
    def cubic(unit: UnitBase) -> UnitBase:
        """Computes the cubic product of the given unit.

        Args:
            unit: The unit the cubic product shall be computed for.

        Returns:
            A new unit holding the cubic product of the given unit.

        """
        return unit * unit * unit

    #############################
    # Basic units and conversions
    #############################

    meter = Base(1.0, "m")

    inch = Base(Prefix.centi * meter * 2.54, "inch")

    feet = Base(inch * 12.0, "ft")

    # Time
    second = Base(1.0, "s")
    minute = Base(second * 60.0, "m")
    hour = Base(minute * 60.0, "h")
    day = Base(hour.value * 24.0, "d")
    # Reference: opm-common; might be changed later on to e,g, Gregorian 365.2524
    year = Base(day.value * 365.0, "y")

    # Volume
    gallon = Base(cubic.__func__(inch) * 231.0, "gal")  # type: ignore[attr-defined]
    stb = Base(gallon * 42.0, "stb")
    barrel = Base(gallon * 42.0, "bbl")
    liter = Base(cubic.__func__(Prefix.deci * meter), "l")  # type: ignore[attr-defined]

    # Mass
    kilogram = Base(1.0, "kg")
    gram = Base(kilogram * 1.0e-3, "g")
    pound = Base(kilogram * 0.45359237, "lb")

    # Energy
    joule = Base(1.0, "J")
    btu = Base(joule * 1054.3503, "BTU")

    # Standardised constant
    gravity = (meter * 9.80665) / square.__func__(second)  # type: ignore[attr-defined]

    ###############################
    # Derived units and conversions
    ###############################

    # Force
    newton = Base(kilogram * meter / square.__func__(second), "N")  # type: ignore[attr-defined]
    dyne = Base(newton * 1.0e-5, "dyn")
    lbf = Base(pound * gravity, "lbf")

    # Pressure
    pascal = Base(newton / square.__func__(meter), "Pa")  # type: ignore[attr-defined]
    bar = Base(pascal * 100000.0, "bar")  # pylint: disable=blacklisted-name
    atm = Base(pascal * 101325.0, "atm")
    psi = Base(lbf / square.__func__(inch), "psi")  # type: ignore[attr-defined]

    # Temperature
    deg_kelvin = Base(1.0, "K")

    deg_celsius = Base(1.0, "\u2103")
    deg_celsius_offset = 273.15

    deg_fahrenheit = Base(5.0 / 9.0, "\u2109")
    deg_fahrenheit_offset = 255.37

    # Viscosity
    pas = pascal * second
    poise = Base(Prefix.deci * pas, "P")

    # Permeability
    p_grad = atm / (Prefix.centi * meter)
    area = square.__func__(Prefix.centi * meter)  # type: ignore[attr-defined]
    flux = cubic.__func__(Prefix.centi * meter) / second  # type: ignore[attr-defined]
    velocity = flux / area
    visc = Base(Prefix.centi * poise, "cP")
    darcy = Base((velocity * visc) / p_grad, "D")

    class Convert:
        @staticmethod
        def from_(value: float, unit: float) -> float:
            return value * unit

        @staticmethod
        def to_(value: float, unit: float) -> float:
            return value / unit
