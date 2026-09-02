try:
    age = int(input("Age: "))
    print("You entered:", age)
except ValueError:
    print("Please enter a number")

try:
    age = int(input("Age: "))
    print("You entered:", age)
except ValueError:
    print("Please enter a number")

print("Program is still running. Next steps can continue here.")

try:
    files = int(input("Enter the number of files: "))
    print(f"Backing up {files} files")
except ValueError:
    print("Please enter the number of files")