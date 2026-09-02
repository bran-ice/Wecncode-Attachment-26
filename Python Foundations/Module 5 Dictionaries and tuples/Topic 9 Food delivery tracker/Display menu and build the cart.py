menu = {
    "Margherita": 8.50,
    "Pepperoni": 9.75,
    "Caesar Salad": 6.25,
    "Garlic Bread": 3.50,
    "Soda": 1.75,
    "Brownie": 2.95
}
# printing the formatted menu
print("Menu:")
for i, (name, price) in enumerate(menu.items(), start=1):
    print(f"{i}. {name} - ${price:.2f}")
cart = {}
while True:
    item_input = input("Enter the item name (type 'done' to finish): ").strip().lower()
    if item_input == "done":
        break

    # find the matching menu key (case-insensitive)
    matched = None
    for name in menu:
        if name.lower() == item_input:
            matched = name
            break

    if not matched:
        print("That item isn't on the menu. Please try again.")
        continue

    qty_str = input(f"Enter quantity for {matched}: ").strip()
    try:
        qty = int(qty_str)
        if qty <= 0:
            print("Quantity must be a positive whole number.")
            continue
    except ValueError:
        print("Please enter a whole number for quantity.")
        continue


    cart[matched] = cart.get(matched, 0) + qty
    print(f"Added {qty} x {matched} to cart.")
subtotal = 0.0
for name, qty in cart.items():
    price = menu[name]
    line_total = qty * price
    subtotal += line_total
    print(f"{name}: {qty} x ${price:.2f} = ${line_total:.2f}")
delivery_fee = 0 if subtotal >= 300 else 50
grand_total = subtotal + delivery_fee

print(f"Subtotal: ${subtotal:.2f}")
if delivery_fee == 0:
    print("Delivery: FREE")
else:
    print(f"Delivery: ${delivery_fee:.2f}")
print(f"Grand total: ${grand_total:.2f}")



