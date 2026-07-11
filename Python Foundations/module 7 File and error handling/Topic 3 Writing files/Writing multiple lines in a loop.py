items = ["Alice: 1500", "Bob: 2000", "Eve: 1750"]

with open("Python Foundations/module 7 File and error handling/Topic 3 Writing files/scores.txt", "a") as file:
    for item in items:
        file.write(f"{item}\n")

names = ["Alice", "Bob", "Eve", "Niru"]

with open("Python Foundations/module 7 File and error handling/Topic 3 Writing files/attendance.txt", "a") as file:
    for name in names:
        file.write(f"{name}\n")