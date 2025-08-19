from decimal import ROUND_DOWN, Decimal, InvalidOperation


def round_to_7_decimal_places(value: Decimal | float | str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("0.0000001"), rounding=ROUND_DOWN)
    except (InvalidOperation, ValueError, TypeError) as err:
        raise ValueError("Invalid coordinate format") from err
