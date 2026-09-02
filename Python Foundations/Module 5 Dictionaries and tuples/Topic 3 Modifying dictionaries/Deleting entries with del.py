student = {"name": "Lena", "grade": "B"}
print("Before:", student)
del student["grade"]
print("After: ", student)
student = {"name": "Lena", "grade": "B", "age": 20}
print("Before:", student)
del student["grade"]
del student["age"]
print("After: ", student)

record = {"user": "branice", "number": 44, "temporary note": "well served"}
print("Before:", record)
del record["temporary note"]
print("After:",record)