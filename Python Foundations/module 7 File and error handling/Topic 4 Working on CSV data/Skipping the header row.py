with open("Python Foundations/module 7 File and error handling/Topic 4 Working on CSV data/contacts.csv", "w") as f:
    f.write("Name,Email,Phone\n")
    f.write("Alice,alice@example.com,555-1234\n")
    f.write("Bob,bob@example.com,555-5678\n")

with open("Python Foundations/module 7 File and error handling/Topic 4 Working on CSV data/contacts.csv", "r") as f:
    lines = f.readlines()
    for line in lines[1:]:
        columns = line.strip().split(",")
        print(columns)

with open("Python Foundations/module 7 File and error handling/Topic 4 Working on CSV data/contacts.csv", "w") as f:
    f.write("Name,Email,Phone\n")
    f.write("  Carol  , carol@example.com , 555-9012\n")
    f.write("\n")
    f.write("Dave,dave@example.com,555-3456\n")

with open("Python Foundations/module 7 File and error handling/Topic 4 Working on CSV data/contacts.csv", "r") as f:
    lines = f.readlines()
    for line in lines[1:]:
        columns = line.strip().split(",")
        print(columns)

with open("Python Foundations/module 7 File and error handling/Topic 4 Working on CSV data/attendance.csv", "w") as f:
    f.write("date,name,present\n")
    f.write("2026-07-12,Branice,yes\n")
    f.write("2026-07-11,Nafula,no\n")
    f.write("2026-07-10,Wafula,yes\n")

with open("Python Foundations/module 7 File and error handling/Topic 4 Working on CSV data/attendance.csv", "r") as f:
    lines = f.readlines()
    for line in lines[1:]:
        columns = line.strip().split(",")
        print(columns)