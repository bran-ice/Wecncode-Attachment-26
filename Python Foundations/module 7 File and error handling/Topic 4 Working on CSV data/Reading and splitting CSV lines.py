with open("Python Foundations/module 7 File and error handling/Topic 4 Working on CSV data/contacts.csv", "w") as f:
    f.write("Alice,alice@example.com,555-1234\n")
    f.write("Bob,bob@example.com,555-5678\n")
    f.write("Carol,carol@example.com,555-9012\n")

with open("Python Foundations/module 7 File and error handling/Topic 4 Working on CSV data/contacts.csv", "r") as f:
    for line in f:
        columns = line.strip().split(",")
        print(columns)
    
with open("Python Foundations/module 7 File and error handling/Topic 4 Working on CSV data/contacts.csv", "w") as f:
    f.write("Name,Email,Phone\n")
    f.write("  Dave  , dave@example.com , 555-0000\n")
    f.write("\n")
    f.write("Eve,eve@example.com,555-2222\n")

with open("Python Foundations/module 7 File and error handling/Topic 4 Working on CSV data/contacts.csv", "r") as f:
    for line in f:
        columns = line.strip().split(",")
        print(columns)
    

with open("Python Foundations/module 7 File and error handling/Topic 4 Working on CSV data/products.csv", "w") as f:
    f.write("Name,Category,Price\n")
    f.write("Screwdriver,Tools,150\n")
    f.write("Hammer,Tools,85\n")
    f.write("Mug,Kitchen,240\n")

with open("Python Foundations/module 7 File and error handling/Topic 4 Working on CSV data/products.csv", "r") as f:
    for line in f:
        columns = line.strip().split(",")
        print(columns)