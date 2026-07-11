text = input("Enter a number: ")
try:
    value = int(text)
except ValueError:
    print("Invalid")
else:
    print(f"Got {value}")
    print("Double:", value * 2)

books = input("Enter the number of books")
try:
    value = int(books)
except ValueError:
    print("Invalid number")
else:
    discount = 10 if value >= 5 else 0
    print(f"Books: {value}, Discount: {discount}%")