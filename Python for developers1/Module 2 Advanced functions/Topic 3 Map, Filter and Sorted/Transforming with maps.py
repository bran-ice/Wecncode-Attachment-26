numbers = [10, 20, 30, 40]
doubled = list(map(lambda x: x * 2, numbers))
print("original:", numbers)
print("doubled:", doubled)
numbers = [10, 20, 30, 40]
incremented = list(map(lambda x: x + 1, numbers))
print("original:", numbers)
print("incremented:", incremented)

temperatures = [44, 45, 38, 36, 28]
temp_F = list(map(lambda t: round(t * 1.8 + 32, 1), temperatures))
print("Original:", temperatures)
print("Converted:", temp_F)