numbers = range(1, 6)
squares = (x ** 2 for x in numbers)
for s in squares:
    print(s)
numbers = range(1, 6)
squares = (x ** 2 for x in numbers)
print(next(squares))
print(next(squares))
for s in squares:
    print(s)

temps_c = [0, 20, 37, 100]
temp_F = (c * 9/5 + 32 for c in temps_c)
print(next(temp_F))
for t in temp_F:
    print(t)
