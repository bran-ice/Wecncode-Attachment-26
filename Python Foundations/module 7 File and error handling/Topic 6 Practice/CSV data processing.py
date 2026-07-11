high_value_order = []
with open("sales.csv", "w") as f:
    f.write("OrderID, Customer, Item, Quantity, TotalPrice\n")
    f.write("100, Wesley, Jersey, 3, 250\n")
    f.write("101, Lah, Boots, 1, 50\n")
with open("sales.csv", "r") as f:
    lines = f.readlines()
    headers = lines[0].strip().split(",")
    orders = []
    for line in lines[1:]:
        column = line.strip().split(",")
        order = {}
        for i in range(len(headers)):
            order[headers[i].strip()] = column[i].strip()
        if int(order["TotalPrice"]) > 100:
            high_value_order.append(order)
for order in high_value_order:
    print(f"Order {order['OrderID']} for {order['Customer']}: {order['Quantity']} x {order['Item']} — ${order['TotalPrice']}")