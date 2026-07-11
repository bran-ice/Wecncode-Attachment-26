with open("Python Foundations/module 7 File and error handling/Topic 2 Reading files/data.txt") as file:
    content = file.read()

print("File contents:")
print(content)

with open("Python Foundations/module 7 File and error handling/Topic 2 Reading files/data.txt") as file:
    content = file.read()
    print("----FILE START----")
    print(content)
    print("----FILE END----")

with open("Python Foundations/module 7 File and error handling/Topic 2 Reading files/student_summary.txt") as file:
    content = file.read()

print("Sending summary:", content.replace("\n", " "))