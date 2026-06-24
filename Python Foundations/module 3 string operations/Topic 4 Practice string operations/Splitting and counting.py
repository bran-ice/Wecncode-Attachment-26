name = input("Enter customers name")
normalised_name = name.strip().title()
price = float(input("Enter the items price"))
print(f"{normalised_name :} ${price: .2f}")
