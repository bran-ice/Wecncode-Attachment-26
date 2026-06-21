while True:
    line = input("Enter text (type quit to stop): ")
    if line == "quit":
        break
    if line == "":
        continue
    print("You entered:", line)
while True:
    line = input("Enter text (type quit to stop): ")
    if line == "quit":
        break
    if line.startswith("#"):
        continue
    print("Processed:", line)
while True:
    email = input("Enter a comment (quit to stop): ")
    if email == "quit":
        break
    if email.strip() == "":
        continue
    if "@" not in email:
        continue
    print(email)
