def calculate_export_total(subtotal: float, discount: float, tax_rate: float) -> float:
    return round((subtotal * (1 + tax_rate)) * (1 - discount), 2)
