PRICES = {
    "A1": 50,  "A2": 120, "A3": 200, "B1": 80,
    "C1": 300, "D1": 45,  "E1": 150, "F1": 90,
}
# Raw inputs
warehouseA = {"A1", "A2", "A3", "A2", "B1", "C1"}
warehouseB = {"B1", "C1", "D1", "D1", "A3", "E1"}
Required = {"A1", "C1", "E1"}
# Cleaning using set comprehension
warehouse_A = {sku.strip() for sku  in warehouseA}
warehouse_B = {sku.strip() for sku in warehouseB}
required_skus = {sku.strip() for sku in Required}
# Set operation for catalogue analysis
stocked_in_both = warehouse_A & warehouse_B
only_in_A = warehouse_A - warehouse_B
only_in_B = warehouse_B - warehouse_A
combined = warehouse_A | warehouse_B
all_required_available = required_skus.issubset(combined)
# Premium count using generator expressions
premium_count = sum(1 for sku in combined if PRICES[sku] >= 100)
total_catalog_value = sum(PRICES[sku] for sku in combined)
# Discounted prices using dict comprehension, sorted and ternary expression
discounted_prices = {
    sku: round(PRICES[sku] * 0.9, 2) if PRICES[sku] > 100 else PRICES[sku]
    for sku in sorted(combined)
}
# Output results formatting
print(f"Stocked in both: {sorted(list(stocked_in_both))}")
print(f"Only in Warehouse A: {sorted(list(only_in_A))}")
print(f"Only in Warehouse B: {sorted(list(only_in_B))}")
print(f"Full catalog: {sorted(list(combined))}")
print(f"All required available: {all_required_available}")
print(f"Premium items (>=100): {premium_count}")
print(f"Total catalog value: {total_catalog_value}")
print(f"Discounted prices: {discounted_prices}")