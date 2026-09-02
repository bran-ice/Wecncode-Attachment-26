employees = {
    "E001": {"name": "Alice", "dept": "Engineering", "salary": 75000},
    "E002": {"name": "Bob",   "dept": "HR",          "salary": 62000}
}

print(employees)                    # whole nested structure
print(employees["E001"])            # inner dictionary for E001
print(employees["E001"]["name"])    # Alice
print(employees["E002"]["salary"])  # 62000

employees = {
    "E001": {"name": "Alice", "dept": "Engineering", "salary": 75000},
    "E002": {"name": "Bob",   "dept": "HR",          "salary": 62000}
}

employees["E002"]["salary"] = 65000
print(employees["E002"]["salary"])

employees = {
    "E001": {"name": "Alice", "dept": "Engineering", "salary": 75000},
    "E002": {"name": "Bob",   "dept": "HR",          "salary": 62000},
    "E003": {"name": "Carol", "dept": "Marketing", "salary": 70000}
}
employees["E002"]["salary"] = employees["E002"]["salary"] + 0.1 * employees["E002"]["salary"]
print(employees["E002"]["salary"])