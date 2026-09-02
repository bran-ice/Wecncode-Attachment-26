employees = [
    {"name": "Asha", "salary": 70000},
    {"name": "Ben", "salary": 85000},
    {"name": "Cara", "salary": 60000}
]
sorted_by_salary_desc = sorted(employees, key=lambda e: e["salary"], reverse=True)
print("original:", employees)
print("sorted by salary (high to low):", sorted_by_salary_desc)
employees = [
    {"name": "Asha", "salary": 70000},
    {"name": "Ben", "salary": 85000},
    {"name": "Cara", "salary": 70000},
    {"name": "Dan", "salary": 60000}
]
sorted_by_salary_asc = sorted(employees, key=lambda e: e["salary"])
print("original:", employees)
print("sorted by salary (low to high):", sorted_by_salary_asc)

books = [
    {"title": "Python", "pages": 322},
    {"title": "Electronics", "pages": 696},
    {"title": "Coding", "pages": 200}
]
sorted_by_pages_asc = sorted(books, key=lambda b: b["pages"])
print("Original:", books)
print("Sorted in ascending order:", sorted_by_pages_asc)