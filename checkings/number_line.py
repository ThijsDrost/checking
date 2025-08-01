from __future__ import annotations

from typing import assert_never


class Bound:
    value: float
    inclusive: bool

    def __init__(self, value, inclusive):
        """
        Represent a bound.

        Attributes
        ----------
        value: float | int
            The value of the bound.
        inclusive: bool
            Whether the bound is inclusive. If True, the bound is inclusive, if False, the bound is exclusive.
            When the bound is infinity or minus infinity, the bound is always stored as inclusive.

        Notes
        -----
        When the bound is infinity or minus infinity, the bound is always stored as inclusive to make the comparison
        easier. And thus infinity is equal to infinity and minus infinity is equal to minus infinity.

        When comparing bounds, there are four possible outcomes:
        - A bound is smaller than another bound, e.g. Bound(1, True) < Bound(2, True)
        - A bound is equal to another bound, e.g. Bound(1, True) == Bound(1, True)
        - A bound is bigger than another bound, e.g. Bound(2, True) > Bound(1, True)
        - A bound is neither bigger, smaller, nor equal to another bound, e.g. Bound(1, True) < Bound(1, False)

        When comparing a bound with a float, the float is considered an inclusive bound.
        """
        if value == float("inf") or value == float("-inf"):
            inclusive = True
        self.value = value
        self.inclusive = inclusive

    def smaller_or_eq(self, other) -> bool:
        """
        Check if the bound value is smaller than the other value (takes into account inclusivity)

        Raises
        ------
        TypeError
            If the comparison is not possible.
        """
        return self <= other

    def bigger_or_eq(self, other) -> bool:
        """
        Checks if the bound value is bigger than the other value (takes into account inclusivity)

        Raises
        ------
        TypeError
            If the comparison is not possible.
        """
        return self >= other

    @staticmethod
    def infinity() -> Bound:
        return Bound(float("inf"), True)

    @staticmethod
    def minus_infinity() -> Bound:
        return Bound(float("-inf"), True)

    def not_comparable(self, other: Bound) -> bool:
        """
        Check if the bound is neither smaller, bigger, nor equal to the other bound.
        This is the case when the bounds have the same value, but different inclusivity.

        Raises
        ------
        TypeError
            If the comparison is not possible.
        """
        if isinstance(other, Bound):
            return self.value == other.value and self.inclusive != other.inclusive
        msg = f"Cannot compare Bound with non Bound {type(other).__name__}"
        raise TypeError(msg)

    def __eq__(self, other: Bound | float) -> bool:
        if isinstance(other, Bound):
            return (self.value == other.value) and (self.inclusive == other.inclusive)
        if isinstance(other, (int, float)):
            return self.inclusive and self.value == other
        return NotImplemented

    def __lt__(self, other: Bound | float) -> bool:
        if isinstance(other, Bound):
            return self.value < other.value
        if isinstance(other, (int, float)):
            return self.value < other
        return NotImplemented

    def __gt__(self, other: Bound | float):
        if isinstance(other, Bound):
            return self.value > other.value
        if isinstance(other, (int, float)):
            return self.value > other
        return NotImplemented

    def __le__(self, other: Bound | float) -> bool:
        if isinstance(other, Bound):
            return self.value < other.value or self == other
        if isinstance(other, (int, float)):
            return self.value < other or self == other
        return NotImplemented

    def __ge__(self, other: Bound | float) -> bool:
        if isinstance(other, Bound):
            return self.value > other.value or self == other
        if isinstance(other, (int, float)):
            return self.value > other or self == other
        return NotImplemented

    def __repr__(self):
        return f"Bound({self.value}, {self.inclusive})"

    def __hash__(self):
        """
        Return a hash of the bound. The hash is based on the value and inclusivity of the bound.
        """
        return hash((self.value, self.inclusive))


MinusInfinity = Bound.minus_infinity()
Infinity = Bound.infinity()


class Range:
    def __init__(self, lower: Bound, upper: Bound, *, _check=True):
        """
        Represent a range of values.

        Notes
        -----
        The Bound class always represents a bound of (minus) infinity as inclusive, when printing these bounds are
        shown as (mathematically) correct exclusive bounds.
        """
        self.lower = lower
        self.upper = upper
        if _check and not self.lower.smaller_or_eq(self.upper):
            msg = f"Lower bound ({self.lower.value}) cannot be bigger than upper bound ({self.upper.value})"
            raise ValueError(msg)

    def __contains__(self, item: float):
        smaller = self.lower <= item
        if smaller is NotImplemented:
            return NotImplemented
        return smaller and self.upper >= item

    def __bool__(self):
        return self.lower <= self.upper

    def __add__(self, other: Range) -> tuple[Range] | tuple[Range, Range]:
        if isinstance(other, Range):
            if (
                (self.lower.value > other.upper.value)
                or (self.upper.value < other.lower.value)
                or (
                    self.lower.value == other.upper.value and (not self.lower.inclusive) and (not other.upper.inclusive)
                )
            ):
                return self, other

            if self.lower.value < other.lower.value:
                lower_bound = self.lower
            elif self.lower.value > other.lower.value:
                lower_bound = other.lower
            else:
                lower_bound = Bound(
                    self.lower.value,
                    self.lower.inclusive or other.lower.inclusive,
                )

            if self.upper.value > other.upper.value:
                upper_bound = self.upper
            elif self.upper.value < other.upper.value:
                upper_bound = other.upper
            else:
                upper_bound = Bound(
                    self.upper.value,
                    self.upper.inclusive or other.upper.inclusive,
                )

            return (Range(lower_bound, upper_bound),)
        return NotImplemented

    def __sub__(
        self,
        other: Range,
    ) -> tuple[Range] | tuple[Range, Range] | tuple[EmptyRange]:
        if isinstance(other, Range):
            lower_bound = Bound(other.lower.value, not other.lower.inclusive)
            upper_bound = Bound(other.upper.value, not other.upper.inclusive)
            if self.lower.bigger_or_eq(upper_bound) or self.upper.smaller_or_eq(
                lower_bound,
            ):
                return (self,)
            if self.lower.smaller_or_eq(lower_bound) and self.upper.bigger_or_eq(
                upper_bound,
            ):
                return Range(self.lower, lower_bound), Range(upper_bound, self.upper)
            if self.lower.smaller_or_eq(lower_bound) and self.upper.smaller_or_eq(
                other.upper,
            ):
                return (Range(self.lower, lower_bound),)
            if self.lower.bigger_or_eq(other.lower) and self.upper.bigger_or_eq(
                upper_bound,
            ):
                return (Range(upper_bound, self.upper),)
            if self.lower.bigger_or_eq(other.lower) and self.upper.smaller_or_eq(
                other.upper,
            ):
                return (EmptyRange,)
            assert_never("This should never happen")
        else:
            return NotImplemented

    def __eq__(self, other: Range) -> bool:
        if not isinstance(other, Range):
            return NotImplemented
        return self.lower == other.lower and self.upper == other.upper

    def __repr__(self):
        return f"Range({self.lower}, {self.upper})"

    def __str__(self):
        lower = "("
        if self.lower.inclusive and self.lower.value != MinusInfinity.value:
            lower = "["
        upper = ")"
        if self.upper.inclusive and self.upper.value != Infinity.value:
            upper = "]"
        return f"{lower}{self.lower.value}, {self.upper.value}{upper}"

    @staticmethod
    def empty():
        """
        Create an empty range. An empty range includes no values.

        Returns
        -------
        Range
        """
        return Range(MinusInfinity, Infinity, _check=False)

    @staticmethod
    def full():
        """
        Create a full range. A full range includes all values.

        Returns
        -------
        Range
        """
        return Range(MinusInfinity, Infinity, _check=False)


EmptyRange = Range(Infinity, MinusInfinity, _check=False)
FullRange = Range(MinusInfinity, Infinity)


class NumberLine:
    def __init__(self, ranges: list[Range] | Range = FullRange, simplify=True):
        """
        A class to represent a number line. All the numbers within the `ranges` are included in the number line.

        Parameters
        ----------
        ranges:
            The ranges which constitute the number line.
        simplify:
            Whether to simplify the ranges by combining them.
        """
        self.ranges: list[Range]

        if isinstance(ranges, Range):
            self.ranges = [ranges]
        elif isinstance(ranges, (list, tuple)):
            self.ranges = list(ranges)
        else:
            msg = f"`NumberLine` can only be created with `Range` or `tuple` of `Range`, not {type(ranges).__name__}"
            raise TypeError(msg)
        if simplify:
            self.simplify()

    def simplify(self):
        """Simplify (inplace) the number line by combining overlapping ranges."""
        busy = True
        if len(self.ranges) <= 1:
            return

        while busy:
            for i, range1 in enumerate(self.ranges[:-1]):
                if range1 == EmptyRange:
                    self.ranges.pop(i)
                    break

                for j, range2 in enumerate(self.ranges[i + 1 :], i + 1):
                    new_range = range1 + range2
                    if len(new_range) == 1:
                        self.ranges[i] = new_range
                        self.ranges.pop(j)
                        break
                else:
                    continue
                break
            else:
                busy = False
        self.ranges.sort(key=lambda x: x.lower.value)

    def check(self, value: float) -> bool:
        """
        Check if a value is in the number line.

        Parameters
        ----------
        value: int | float

        Returns
        -------
        bool

        Raises
        ------
        TypeError
            If the value is not an int or a float.
        """
        contains = self.__contains__(value)
        if contains is NotImplemented:
            msg = f"Cannot check for type {type(value).__name__} in NumberLine, only int and float are allowed"
            raise TypeError(msg)
        return contains

    contains = check

    def raise_check(self, value):
        """
        Raise a ValueError if the value is not in the number line.

        Parameters
        ----------
        value: int | float

        Raises
        ------
        ValueError
            If the value is not in the number line.
        """
        err = self.return_raise_check(value)
        if err is not None:
            raise err

    def return_raise_check(self, value):
        """
        Return a ValueError if the value is not in the number line.

        Parameters
        ----------
        value: int | float

        Returns
        -------
        ValueError | None
            Return ValueError if the value is not in the number line, else returns None.
        """
        if not self.check(value):
            if len(self.ranges) == 1:
                if self.ranges[0].lower == MinusInfinity:
                    or_equal = "or equal to " if self.ranges[0].upper.inclusive else ""
                    return ValueError(
                        f"{value} should be smaller than {or_equal}{self.ranges[0].upper.value}",
                    )
                if self.ranges[0].upper == Infinity:
                    or_equal = "or equal to " if self.ranges[0].lower.inclusive else ""
                    return ValueError(
                        f"{value} should be bigger than {or_equal}{self.ranges[0].lower.value}",
                    )
                return ValueError(
                    f"{value} should be in the range {self.ranges[0]}",
                )
            return ValueError(f"{value} should be in: {self}")
        return None

    def __add__(
        self,
        other: NumberLine | Range | float,
    ) -> NumberLine | NotImplemented:
        if isinstance(other, NumberLine):
            return NumberLine(self.ranges + other.ranges)
        if isinstance(other, Range):
            return NumberLine([*self.ranges, other])
        if isinstance(other, (int, float)):
            return NumberLine(
                [*self.ranges, Range(Bound(other, True), Bound(other, True))],
            )
        return NotImplemented

    def __sub__(
        self,
        other: NumberLine | Range | float,
    ) -> NumberLine | NotImplemented:
        def subtract_range(_ranges, range_):
            new_ranges = []
            for _range in _ranges:
                new_range = _range - range_
                if isinstance(new_range, Range):
                    new_ranges.append(new_range)
                else:
                    new_ranges.extend(new_range)
            return new_ranges

        if isinstance(other, NumberLine):
            new_ranges = self.ranges
            for range_ in other.ranges:
                new_ranges = subtract_range(new_ranges, range_)
            return NumberLine(new_ranges, simplify=False)
        if isinstance(other, Range):
            return NumberLine(subtract_range(self.ranges, other), simplify=False)
        if isinstance(other, (int, float)):
            return NumberLine(
                subtract_range(
                    self.ranges,
                    Range(Bound(other, True), Bound(other, True)),
                ),
                simplify=False,
            )
        return NotImplemented

    def __contains__(self, value: float) -> bool | NotImplemented:
        if isinstance(value, (float, int)):
            return any(value in _range for _range in self.ranges)
        return NotImplemented

    def __bool__(self) -> bool:
        self.simplify()
        return bool(self.ranges)

    def __repr__(self):
        return f"NumberLine({self.ranges})"

    def __str__(self):
        return f"NumberLine({', '.join(str(range_) for range_ in self.ranges)})"

    def __invert__(self):
        return NumberLine.full() - self

    @staticmethod
    def include_from_floats(
        start=float("-inf"),
        end=float("inf"),
        start_inclusive=True,
        end_inclusive=True,
    ):
        """
        Create a number line including all values between the `start` and `end` value.

        Parameters
        ----------
        start: int | float
            The lower bound of the number line.
        end: int | float
            The upper bound of the number line.
        start_inclusive: bool
            Whether the lower bound is inclusive.
        end_inclusive: bool
            Whether the upper bound is inclusive.

        Returns
        -------
        NumberLine
        """
        return NumberLine.include(
            Bound(start, start_inclusive),
            Bound(end, end_inclusive),
        )

    between_from_floats = include_from_floats

    @staticmethod
    def empty():
        """
        Create an empty number line. An empty number line includes no values.

        Returns
        -------
        NumberLine
        """
        return NumberLine()

    @staticmethod
    def full():
        """
        Create a full number line. A full number line includes all values.

        Returns
        -------
        NumberLine
        """
        return NumberLine(FullRange)

    @staticmethod
    def include(start=MinusInfinity, end=Infinity):
        """
        Create a number line including all values between the `start` and `end` bound.

        Parameters
        ----------
        start: Bound
            The lower bound of the number line.
        end: Bound
            The upper bound of the number line.

        Returns
        -------
        NumberLine
        """
        if start.bigger_or_eq(end):
            msg = f"Start value ({start.value}) cannot be bigger than end value ({end.value})"
            raise ValueError(msg)
        return NumberLine(Range(start, end))

    between = include

    @staticmethod
    def include_float(
        start: float,
        end: float,
        start_inclusive=True,
        end_inclusive=True,
    ):
        """
        Create a number line including all values between the `start` and `end` value.

        Parameters
        ----------
        start: int | float
            The lower bound of the number line.
        end: int | float
            The upper bound of the number line.
        start_inclusive: bool
            Whether the lower bound is inclusive.
        end_inclusive: bool
            Whether the upper bound is inclusive.

        Returns
        -------
        NumberLine
        """
        return NumberLine.include(
            Bound(start, start_inclusive),
            Bound(end, end_inclusive),
        )

    between_float = include_float

    @staticmethod
    def bigger_than(value: Bound):
        """
        Create a number line including all values bigger than the `value`.

        Parameters
        ----------
        value: Bound

        Returns
        -------
        NumberLine
        """
        return NumberLine.include(value, Infinity)

    @staticmethod
    def bigger_than_float(value: float, inclusive=True):
        """
        Create a number line including all values bigger than the `value`.

        Parameters
        ----------
        value: int | float
        inclusive: bool

        Returns
        -------
        NumberLine
        """
        return NumberLine.include_from_floats(start=value, start_inclusive=inclusive)

    @staticmethod
    def smaller_than(value):
        """
        Create a number line including all values smaller than the `value`.

        Parameters
        ----------
        value: Bound

        Returns
        -------
        NumberLine
        """
        return NumberLine.include(MinusInfinity, value)

    @staticmethod
    def smaller_than_float(value, inclusive=True):
        """
        Create a number line including all values smaller than the `value`.

        Parameters
        ----------
        value: int | float
        inclusive: bool

        Returns
        -------
        NumberLine
        """
        return NumberLine.include_from_floats(end=value, end_inclusive=inclusive)

    @staticmethod
    def exclude(start, end):
        """
        Create a number line excluding all values between the `start` and `end` bound.

        Parameters
        ----------
        start: Bound
        end: Bound

        Returns
        -------
        NumberLine
        """
        if start.bigger_or_eq(end):
            msg = f"Start value ({start.value}) cannot be bigger than end value ({end.value})"
            raise ValueError(msg)
        if start == MinusInfinity and end == Infinity:
            return NumberLine.empty()
        return NumberLine([Range(MinusInfinity, start), Range(end, Infinity)])

    outside = exclude

    @staticmethod
    def exclude_from_floats(
        start=float("-inf"),
        end=float("inf"),
        start_inclusive=True,
        end_inclusive=True,
    ):
        """
        Create a number line excluding all values between the `start` and `end` value.

        Parameters
        ----------
        start: int | float
        end: int | float
        start_inclusive: bool
        end_inclusive: bool

        Returns
        -------
        NumberLine
        """
        return NumberLine.exclude(
            Bound(start, start_inclusive),
            Bound(end, end_inclusive),
        )

    outside_from_floats = exclude_from_floats

    @staticmethod
    def positive(include_zero=True):
        """
        Create a number line including all positive values.

        Parameters
        ----------
        include_zero: bool
            Whether to include zero.

        Returns
        -------
        NumberLine
        """
        return NumberLine.bigger_than_float(0, include_zero)

    @staticmethod
    def negative(include_zero=True):
        """
        Create a number line including all negative values.

        Parameters
        ----------
        include_zero: bool
            Whether to include zero.

        Returns
        -------
        NumberLine
        """
        return NumberLine.smaller_than_float(0, include_zero)
