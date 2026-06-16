product_name = input("What is the product name?")
unit_price = float(input("what is the unit price?"))
quantity = int(input("how many were bought"))
shipping_fee = float(input("What is the shipping fee?"))
subtotal = unit_price * quantity
grandtotal = subtotal + shipping_fee
points = grandtotal // 10
print("Product:" , product_name)
print("Subtotal: $" , subtotal)
print("Grandtotal: $" , grandtotal)
print("Loyalty Points:" , points)