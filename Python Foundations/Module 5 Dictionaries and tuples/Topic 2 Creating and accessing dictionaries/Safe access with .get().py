student = {"name": "Alice", "age": 20}

# .get(key, default) returns the value for key if present, otherwise returns default
print(student.get("name", "Unknown"))
print(student.get("email", "N/A"))
student = {"name": "Alice", "age": 20, "gpa": 3.8}
print(student.get("gpa", "N/A"))
print(student.get("email"))

review = {"quality": "good", "size": "large"}
print(review.get("comment", "No comment"))
print(review.get("rating", "No rating"))