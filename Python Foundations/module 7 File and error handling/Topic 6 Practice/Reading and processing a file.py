with open("inventory_audit.txt", "w") as f:
    f.write("ISBN, title, quantity, price\n")
    f.write("9780143127741, The Night Watch , 12 , 9.99\n")
    f.write("9780553382563, Deep Work,5,15.50\n")
    f.write("9780307271037, The Road, 20 , 8.75\n")
    f.write("9780671027032, Beloved ,7,12.40\n")
    f.write("9780140449136, The Odyssey, 10, 11.25\n")

with open("inventory_audit.txt", "r") as f:
    lines = f.readlines()

# Clean and parse the header names
headers = [h.strip() for h in lines[0].strip().split(",")]

rows = []
for line in lines[1:]:
    columns = [c.strip() for c in line.strip().split(",")]
    # Build a dict with cleaned string values
    row = {headers[i]: columns[i] for i in range(len(headers))}
    # Convert quantity and price to numeric types for arithmetic
    row["quantity"] = int(columns[2])
    row["price"] = float(columns[3])
    rows.append(row)

# Print a formatted summary
print("Inventory Summary")
print("-----------------")
for r in rows:
    title = r["title"]
    qty = r["quantity"]
    price = r["price"]
    total_value = qty * price
    print(f"{title} — Quantity: {qty}, Unit Price: ${price:.2f}, Total Value: ${total_value:.2f}")