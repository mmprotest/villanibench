def calculate_export_total(subtotal: float, discount_amount: float, tax_rate: float) -> float:
    return round(subtotal * (1 + tax_rate) - discount_amount, 2)
