def calculate_export_total(subtotal: float, discount_amount: float, tax_rate: float) -> float:
    taxed = subtotal * (1 + tax_rate)
    return round(taxed - discount_amount, 2)
