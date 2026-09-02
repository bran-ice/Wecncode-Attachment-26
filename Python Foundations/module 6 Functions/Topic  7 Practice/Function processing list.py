orders = [29.99, 120.00, 15.50, 60.25]

def calculate_total_sales(orders):
    total = 0.0
    for order in orders:
        total += order
    return total
final_revenue = calculate_total_sales(orders)
print(f"Total sales for today's orders: ${final_revenue:,.2f}")