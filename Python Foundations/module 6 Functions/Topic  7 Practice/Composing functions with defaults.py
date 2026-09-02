subtotals = [12.00, 25.50, 8.75, 40.00]

def add_packaging(subtotal):
    return subtotal + subtotal * 0.05

def final_price(subtotal, service_fee=1.50):
    amount_with_packaging = add_packaging(subtotal)
    return amount_with_packaging + service_fee

for subtotal in subtotals:
    total = final_price(subtotal)
    print(f"Final price for ${subtotal:.2f} subtotal is ${total:.2f}")