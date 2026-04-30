def compute_total(subtotal, shipping, discount, tax):
    # BUG: source-of-truth implementation is stale.
    return subtotal * (1 + tax) + shipping - discount
