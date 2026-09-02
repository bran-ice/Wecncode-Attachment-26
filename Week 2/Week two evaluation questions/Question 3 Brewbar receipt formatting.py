raw_name = input("Enter Item name: ").strip()
unit_price = float(input("Enter Unit price: "))
quantity = int(input("Enter Quantity: "))
coupon = input("Enter Coupon code: ").strip().upper()
item_name = raw_name.title()
line_total = unit_price * quantity
discount_amount = 0.0
if coupon == "SAVE10":
        discount_amount = line_total * 0.10
        discount_line = f"Discount ({coupon}): -${discount_amount:.2f}"
elif coupon == "SAVE20":
        discount_amount = line_total * 0.20
        discount_line = f"Discount ({coupon}): -${discount_amount:.2f}"
else:
        discount_line = "Discount: none"
you_pay = line_total - discount_amount
print(f"Item: {item_name}")
print(f"Unit Price: ${unit_price:.2f}")
print(f"Quantity: {quantity}")
print(f"Line Total: ${line_total:.2f}")
print(discount_line)
print(f"You Pay: ${you_pay:.2f}")
