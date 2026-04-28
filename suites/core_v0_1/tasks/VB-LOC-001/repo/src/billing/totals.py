def calculate_export_total(subtotal: float, discount_amount: float, tax_rate: float) -> float:
    # BUG: discount amount is subtracted after tax. Fixed discounts must reduce taxable subtotal.
    return round(subtotal * (1 + tax_rate) - discount_amount, 2)
