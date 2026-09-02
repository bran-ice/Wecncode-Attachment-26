square = lambda x: x ** 2
print(square(5))
add = lambda a, b: a + b
print(add(3, 4))
pairs = [("Alice", 30), ("Bob", 25), ("Carol", 27)]
sorted_by_age = sorted(pairs, key=lambda p: p[1])
print(sorted_by_age)

words  = []
while True: 
    entry = input("Enter the words(enter stop to end)")
    if entry == "stop":
        break
    words.append(entry)
lengths = list(map(lambda w: len(w), words))
print(lengths)
    