returns_records = [
    {"item_name": "Vintage Denim Jacket", "return_count": 58},
    {"item_name": "Classic Tee", "return_count": 42},
    {"item_name": "Running Shoes", "return_count": 27},
    {"item_name": "Leather Belt", "return_count": 13},
    {"item_name": "Silk Scarf", "return_count": 8},
    {"item_name": "Beanie", "return_count": 3},
]

sorted_returns = sorted(
    returns_records, key=lambda x: x["return_count"], reverse=True
)

formatted_reports = list(
    map(
        lambda record: f"{record['item_name']} - Returns: {record['return_count']}",
        sorted_returns,
    )
)

for report in formatted_reports:
    print(report)