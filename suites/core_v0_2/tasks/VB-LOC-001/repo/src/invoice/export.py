from billing.totals import calculate_export_total


def export_invoice_total(subtotal: float, discount_amount: float, tax_rate: float) -> float:
    return calculate_export_total(subtotal, discount_amount, tax_rate)
