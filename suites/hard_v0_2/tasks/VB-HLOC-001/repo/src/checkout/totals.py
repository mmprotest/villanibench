def compute_total(subtotal, shipping, discount, tax):
    # Shipping discount cannot reduce the order below subtotal plus tax.
    return subtotal * (1 + tax) + max(shipping - discount, 0)
