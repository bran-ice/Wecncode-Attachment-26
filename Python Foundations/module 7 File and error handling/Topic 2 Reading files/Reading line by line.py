with open("Python Foundations/module 7 File and error handling/Topic 2 Reading files/tasks.txt") as file:
    print("Remaining tasks:")
    for line in file:
        print(line.strip())

with open("Python Foundations/module 7 File and error handling/Topic 2 Reading files/data.txt") as file:
    lines = file.readlines()

print("First line:", lines[0].strip())