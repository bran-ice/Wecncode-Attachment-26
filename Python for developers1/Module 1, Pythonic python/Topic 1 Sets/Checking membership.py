guests = {"Alice", "Bob", "Charlie"}

if "Bob" in guests:
    print("Bob is on the guest list")
else:
    print("Bob is not on the guest list")

if "Dana" not in guests:
    print("Dana is not on the guest list")

guests = {"Alice", "Bob", "Charlie"}

print("Alice" in guests)
print("Eve" in guests)

if "Charlie" in guests:
    print("Welcome, Charlie")

if "Eve" not in guests:
    print("Eve, please register")

books = {"Dune", "The Hobbit"}
if "Dune" in books:
    print("Available")
else:
    print("Not available")
if "Neuromancer" in books:
    print("Available")
else:
    print("Not available")