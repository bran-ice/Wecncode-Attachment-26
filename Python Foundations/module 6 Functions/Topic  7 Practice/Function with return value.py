distance = float(input("Enter the distance"))
weight = float(input("Enter the weight"))
base_fee = 5.00

def calculate_total(distance, weight):
    total = base_fee + 0.1 * distance + 2.00 * weight
    return total
total = calculate_total(distance, weight)
print(f"Total shipping cost for {weight} km over {distance} km is {total}")