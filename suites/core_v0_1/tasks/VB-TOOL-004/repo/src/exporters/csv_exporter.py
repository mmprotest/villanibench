def export_csv(rows):
    return "\n".join(",".join(map(str, row)) for row in rows)
