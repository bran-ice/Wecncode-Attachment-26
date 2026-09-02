while True:
    command = input("Enter command (type quit to stop): ")
    if command == "quit":
        break
    print("You entered:", command)
while True:
    password = input("Enter password: ")
    if password == "letmein":
        print("Access granted")
        break
    print("Wrong password, try again")
while True:
    command = input("Send command to robot (type stop to end): ")
    if command == "stop":
        print("Shutting down robot")
        break
    print("Command queued:", command)
while True:
    command = input("Enter guest name (type quit to end): ")
    if command == "quit":
        break
    print("Welcome", command)