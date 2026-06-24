employees = {
    "E001": {"name": "Alice", "dept": "Engineering", "salary": 75000},
    "E002": {"name": "Bob",   "dept": "HR",          "salary": 62000}
}

# Directly change the nested value by chaining keys
employees["E001"]["salary"] = 80000
print(employees["E001"]["salary"])

# Or access the inner dictionary first, then the field
record = employees["E001"]
print(record["salary"])

employees = {
    "E001": {"name": "Alice", "dept": "Engineering", "salary": 75000},
    "E002": {"name": "Bob", "dept": "HR", "salary": 62000}
}

record = employees["E001"]
record["salary"] = record["salary"] + 5000
print(record["salary"])
print(employees["E001"]["salary"])

departments = {
    "HR": {"manager": {"name": "Branice", "salary": 75000}}
}
departments["HR"]["manager"]["salary"] = departments["HR"]["manager"]["salary"] + 0.15 * departments["HR"]["manager"]["salary"]
print(departments["HR"]["manager"]["salary"])