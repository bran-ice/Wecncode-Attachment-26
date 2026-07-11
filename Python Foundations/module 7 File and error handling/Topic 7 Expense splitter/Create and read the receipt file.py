with open("Python Foundations/module 7 File and error handling/Topic 7 Expense splitter/receipt.txt", "w") as f:
    f.write("Ugali, 25.50\n")
    f.write("Kunde, 20.50\n")
    f.write("Spinach, 35.00\n")
    f.write("Burger, 115.65\n")
    f.write("Fries, 90.50\n")
    f.write("Chicken wings, 110.00\n")
items = []
try:
    with open("Python Foundations/module 7 File and error handling/Topic 7 Expense splitter/receipt.txt", "r") as file:
        for line in file:
            line = line.strip()
            try:
                parts = line.split(",")
                name = parts[0].strip()
                price = float(parts[1].strip())
                item = {"name": name, "price": price}
                items.append(item)
            except (ValueError, IndexError):
                continue
        print(items)
except FileNotFoundError:
    print("File not found")