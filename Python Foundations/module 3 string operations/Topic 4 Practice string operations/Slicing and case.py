customers_note = input("Enter the customers note")
tag = (customers_note[0 : 1], customers_note[len(customers_note) // 2 : len(customers_note) // 2 + 1], customers_note[-1 : ])
quick_tag = "".join(tag).upper()
print("Quick tag:" , quick_tag)