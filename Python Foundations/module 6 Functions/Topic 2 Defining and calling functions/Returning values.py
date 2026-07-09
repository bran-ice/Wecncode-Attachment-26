def calculate_total(price, tax_rate, shipping):
    total = price + price * tax_rate + shipping
    return total

order_total = calculate_total(100, 0.08, 5)
print(order_total)

def calculate_total(price, tax_rate, shipping):
    total = price + price * tax_rate + shipping
    return total

subtotal1 = calculate_total(50, 0.07, 4)
subtotal2 = calculate_total(30, 0.07, 4)
grand_total = subtotal1 + subtotal2
print(grand_total)

def average(x, y, z):
    avg = (x + y + z) / 3
    return avg

result = average(90, 85, 78)
print(result)