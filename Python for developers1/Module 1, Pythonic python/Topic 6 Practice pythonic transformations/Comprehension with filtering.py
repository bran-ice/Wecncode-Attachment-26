wines = []
while True:
    name = input("Enter the name of the wine(press Enteron an empty line to stop)")
    if name == "":
        if len(wines) >= 5:
            break
    else:
        wines.append(name)
        if len(wines) == 5:
            break
filtered_wines = [w for w in wines if "reserve" in w.lower()]
wine_dict = {w: len(w) for w in filtered_wines}
for wine, length in wine_dict.items():
    print(f"{wine}: {length}")