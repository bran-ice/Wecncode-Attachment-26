a = 1
b = 2
print("before:", a, b)
a, b = b, a
print("after: ", a, b)

left = 30
right =70
left, right = right, left
print(left)
print(right)