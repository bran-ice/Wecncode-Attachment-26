numbers = range(1, 6)
total = sum(x ** 2 for x in numbers)
print(total)
scores = [10, -1, 5]
print(any(score < 0 for score in scores))
print(all(score >= 0 for score in scores))

words = ["apple", "banana", "cherry", "date"]
length = max(len(word) for word in words)
print(length)