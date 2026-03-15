from decimal import Decimal, ROUND_HALF_UP

def round_to_7_decimal_places(v):
    if v is None:
        return None
    if isinstance(v, (float, int, str)):
        v = Decimal(str(v))
    return v.quantize(Decimal("0.0000001"), rounding=ROUND_HALF_UP)
