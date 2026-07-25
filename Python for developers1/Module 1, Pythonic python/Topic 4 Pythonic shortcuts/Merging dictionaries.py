defaults = {"theme": "light", "font_size": 12}
user_settings = {"font_size": 14, "language": "en"}
merged = {**defaults, **user_settings}
print(merged)

defaults = {"theme": "light", "font_size": 12}
user_settings = {"font_size": 14, "language": "en"}
merged = {**user_settings, **defaults}
print(merged)

product_defaults = {"name": "T-shirt", "price": 20.0, "color": "white", "in_stock": True}
sale_overrides = {"price": 15.0, "color": "red", "on_sale": True}
merged = {**product_defaults, **sale_overrides}
print(merged)