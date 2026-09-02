student = {"name": "Lena", "age": 20}
print("Before:", student)
age = student.pop("age")
print("Removed age:", age)
print("After: ", student)
student = {"name": "Lena", "age": 20, "grade": "B"}
print("Before:", student)
grade = student.pop("grade")
print("Removed grade:", grade)
print("After: ", student)

record ={"Name": "Branice", "salary": 30000, "position": "Entry level"}
print("Before:", record)
salary = record.pop("salary")
print("Removed salary:", salary)
print("After:", record)