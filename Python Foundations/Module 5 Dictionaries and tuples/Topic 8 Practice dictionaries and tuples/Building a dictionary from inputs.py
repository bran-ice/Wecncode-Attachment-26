price_list = {}
while True:
    item = input("Item name (enter '' to stop) ")
    item = item.strip()
    if item == '':
        break
    if price_list.get(item) is not None:
        print("That item already exists — skipping.")
        continue
    price = float(input("Price: "))
    price_list[item] = price

for item, price in price_list.items():
    print(f"{item}: {price}")