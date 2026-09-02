with open("Python Foundations/module 7 File and error handling/Topic 4 Working on CSV data/contacts.csv", "w") as f:
    f.write("name,email,city\n")
    f.write("Alice,alice@example.com,Seattle\n")
    f.write("Bob,bob@example.com,Portland\n")
    f.write("Carol,carol@example.com,San Francisco\n")

with open("Python Foundations/module 7 File and error handling/Topic 4 Working on CSV data/contacts.csv", "r") as f:
    lines = f.readlines()
    headers = lines[0].strip().split(",")
    rows = []
    for line in lines[1:]:
        columns = line.strip().split(",")
        row = {}
        for i in range(len(headers)):
            row[headers[i]] = columns[i]
        rows.append(row)

for record in rows:
    print(record)

with open("Python Foundations/module 7 File and error handling/Topic 4 Working on CSV data/contacts.csv", "r") as f:
    lines = f.readlines()
    headers = lines[0].strip().split(",")
    rows = []
    for line in lines[1:]:
        columns = line.strip().split(",")
        row = {}
        for i in range(len(headers)):
            row[headers[i]] = columns[i]
        rows.append(row)

for record in rows:
    print(record["email"])

with open("Python Foundations/module 7 File and error handling/Topic 4 Working on CSV data/events.csv", "w") as f:
    f.write("date,start_time,event\n")
    f.write("2026-07-10,9:00,Team meeting\n")
    f.write("2026-07-18,12:30,Rotations\n")
    f.write("2026-07-19,4:00,Orientation\n")

with open("Python Foundations/module 7 File and error handling/Topic 4 Working on CSV data/events.csv", "r") as f:
    lines = f.readlines()
    headers = lines[0].strip().split(",")
    rows = []
    for line in lines[1:]:
        columns = line.strip().split(",")
        row = {}
        for i in range(len(headers)):
            row[headers[i]] = columns[i]
        rows.append(row)

for event in rows:
    print(event["date"], event["start_time"], "-", event["event"])