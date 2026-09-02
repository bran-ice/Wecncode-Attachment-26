order_amount = float(input("What is the order amount?"))

distance = float(input("Give the distance"))
if distance <= 3:
    base_fee = 20
elif distance <= 7:
    base_fee = 40
else:
    base_fee = 70
final_price = base_fee

if order_amount >= 500:
    final_price = 0

peak_hour = input("Is it a peak hour?(yes/no)")
normalised_peak_hour = peak_hour .strip().lower()


print(f"Distance Tier Fee: ${base_fee}")
if final_price == 0:
    print("Free delivery unlocked! You pay: ₹0")
else:
    print(f"Delivery Fee: ${final_price}")