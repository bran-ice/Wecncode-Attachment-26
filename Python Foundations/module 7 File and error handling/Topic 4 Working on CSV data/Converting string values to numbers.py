with open("Python Foundations/module 7 File and error handling/Topic 4 Working on CSV data/salaries.csv", "w") as f:
    f.write("name,salary\n")
    f.write("Alice,75000\n")
    f.write("Bob,62000\n")
    f.write("Carol,58000.50\n")

with open("Python Foundations/module 7 File and error handling/Topic 4 Working on CSV data/salaries.csv", "r") as f:
    lines = f.readlines()
    for line in lines[1:]:
        columns = line.strip().split(",")
        salary_str = columns[1]
        salary_float = float(salary_str)
        salary_int = int(salary_float)
        print(columns[0], "salary as string:", salary_str)
        print(columns[0], "as float:", salary_float)
        print(columns[0], "as int (truncated):", salary_int)
        print(columns[0], "after 10% raise (float):", salary_float * 1.10)

with open("Python Foundations/module 7 File and error handling/Topic 4 Working on CSV data/salaries.csv", "w") as f:
    f.write("name,salary\n")
    f.write("Alice,75000\n")
    f.write("Bob,62000\n")
    f.write("Carol,58000.50\n")

with open("Python Foundations/module 7 File and error handling/Topic 4 Working on CSV data/salaries.csv", "r") as f:
    lines = f.readlines()
    for line in lines[1:]:
        columns = line.strip().split(",")
        salary_str = columns[1]
        salary_float = float(salary_str)
        salary_int = int(salary_float)
        print(columns[0], "salary as float:", salary_float)
        print(columns[0], "as int(truncated):", salary_int)

with open("Python Foundations/module 7 File and error handling/Topic 4 Working on CSV data/temperature.csv", "w") as f:
    f.write("date, temp_c\n")
    f.write("2026-07-10,21.5\n")
    f.write("2026-07-11,19\n")
    f.write("2026-07-12,23.0\n")
with open("Python Foundations/module 7 File and error handling/Topic 4 Working on CSV data/temperature.csv", "r") as f:
    lines = f.readlines()
    for line in lines[1:]:
        columns = line.strip().split(",")
        temperature_string = columns[1]
        temperature_float = float(temperature_string)
        temperature_fahranheit = (temperature_float * 1.8) + 32
        temperature_int = int(temperature_float)
        print(columns[0], temperature_fahranheit)