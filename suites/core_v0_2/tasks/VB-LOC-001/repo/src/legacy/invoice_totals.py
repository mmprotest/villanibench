def calculate_export_total(subtotal: float, discount_amount: float, tax_rate: float) -> float:
    return round((subtotal - discount_amount) * (1 + tax_rate), 2)
