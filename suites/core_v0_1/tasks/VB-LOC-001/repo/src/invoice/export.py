from billing.totals import calculate_export_total

def export_invoice_total(subtotal: float, discount: float, tax_rate: float) -> float:
    return calculate_export_total(subtotal, discount, tax_rate)
