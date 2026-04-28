def calculate_export_total(subtotal: float, discount: float, tax_rate: float) -> float:
    taxed = subtotal * (1 + tax_rate)
    return round(taxed * (1 - discount), 2)
