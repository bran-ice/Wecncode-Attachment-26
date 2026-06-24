# Top-sellers displayed by rank (position matters)
top_products = ["Laptop", "Headphones", "Smartphone", "Camera"]
print(top_products[0])  # #1 product
print(top_products[2])  # #3 product

for product in top_products:
    print(product)  # prints products in rank order


# Ranking kept as a list of SKUs (position matters)
top_products = ["SKU100", "SKU200", "SKU300", "SKU400"]
print(top_products[0])  # #1 SKU

# Product details stored in a dictionary keyed by SKU (label-based)
products = {
    "SKU100": {"name": "Laptop", "price": 999, "stock": 5},
    "SKU200": {"name": "Headphones", "price": 199, "stock": 12},
    "SKU300": {"name": "Smartphone", "price": 699, "stock": 8},
    "SKU400": {"name": "Camera", "price": 499, "stock": 3},
}

# Display in rank order using the list of SKUs
for sku in top_products:
    print(products[sku]["name"])

# Fast direct lookup when a user clicks a product
print(products["SKU300"]["price"])  # direct access by SKU

# Iterate through all products by label
for sku, info in products.items():
    print(sku, info["name"], info["stock"])