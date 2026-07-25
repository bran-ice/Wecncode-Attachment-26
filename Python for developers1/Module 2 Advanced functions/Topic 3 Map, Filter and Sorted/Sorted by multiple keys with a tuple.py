employees = [
    {"name": "Asha", "department": "HR",   "salary": 70000},
    {"name": "Ben",  "department": "Eng",  "salary": 85000},
    {"name": "Cara", "department": "HR",   "salary": 60000},
    {"name": "Dan",  "department": "Eng",  "salary": 92000},
    {"name": "Eli",  "department": "Sales","salary": 75000}
]

sorted_employees = sorted(employees, key=lambda e: (e["department"], -e["salary"]))
print("original:", employees)
print("sorted by department, then salary (high to low):", sorted_employees)
employees = [
    {"name": "Asha", "department": "HR",   "salary": 70000},
    {"name": "Ben",  "department": "Eng",  "salary": 85000},
    {"name": "Cara", "department": "HR",   "salary": 60000},
    {"name": "Dan",  "department": "Eng",  "salary": 92000},
    {"name": "Eli",  "department": "Sales","salary": 75000}
]

sorted_employees_asc = sorted(employees, key=lambda e: (e["department"], e["salary"]))
print("sorted by department, then salary (low to high):", sorted_employees_asc)

movies = [
    {"title": "Moonlight",               "genre": "Drama",       "year": 2016},
    {"title": "Parasite",                "genre": "Drama",       "year": 2019},
    {"title": "The Grand Budapest Hotel","genre": "Comedy",      "year": 2014},
    {"title": "Superbad",                "genre": "Comedy",      "year": 2007},
    {"title": "Arrival",                 "genre": "Sci-Fi",      "year": 2016},
    {"title": "Blade Runner 2049",       "genre": "Sci-Fi",      "year": 2017},
    {"title": "Mad Max: Fury Road",      "genre": "Action",      "year": 2015},
    {"title": "Free Solo",               "genre": "Documentary", "year": 2018}
]
sorted_movies_asc = sorted(movies, key=lambda m:(m["genre"], -m["year"]))
print("Original:", movies)
print("Sorted list:", sorted_movies_asc)