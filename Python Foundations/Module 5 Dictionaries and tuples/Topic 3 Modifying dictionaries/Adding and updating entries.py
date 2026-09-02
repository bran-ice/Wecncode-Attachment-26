student = {"name": "Alice", "age": 20}
print(student)
student["email"] = "alice@uni.edu"
print(student)
student["age"] = 21
print(student)
student = {"name": "Alice", "age": 20}
print("Before:", student)
student["age"] = student["age"] + 1
print("After: ", student)

book = {"title": "Python", "copies": 10}
print(book)
book["copies"] = book["copies"] - 1
print(book)
book["borrower"] = "patron"
print(book)