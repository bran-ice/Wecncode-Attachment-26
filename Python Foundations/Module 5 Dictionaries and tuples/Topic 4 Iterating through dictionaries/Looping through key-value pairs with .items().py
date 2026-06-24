students = {"Alice": 88, "Ben": 92, "Carla": 79}

for name, grade in students.items():
    print(f"{name}: {grade}")

students = {"Alice": 88, "Ben": 92, "Carla": 79}

for name, grade in students.items():
    print(f"{grade} - {name}")

employees = {"E100": "Marketing", "E101": "Accounts", "E102": "Sales"}

for IDs, department in employees.items():
    print(f"Employee {IDs} works in {department}")