def divide(a, b):
    return a // b, a % b

quotient, remainder = divide(17, 5)
print("quotient:", quotient)
print("remainder:", remainder)

def divide(a, b):
    return a // b, a % b

result = divide(20, 6)
print(result)

quotient, remainder = result
print("quotient:", quotient)
print("remainder:", remainder)

def width_and_height(a, b):
    area = a * b
    perimeter = (a + b)*2
    return area, perimeter

area, perimeter = width_and_height(12, 8)
print(area)
print(perimeter)
    
