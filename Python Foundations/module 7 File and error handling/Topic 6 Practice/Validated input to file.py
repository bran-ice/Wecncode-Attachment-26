count = []
while True:
    guests = input("Enter the number of guests(type done to finish)")
    if guests == "done":
        break
    try:
     int(guests)
    except ValueError:
     print("Invalid entry")
     continue
    count.append(guests)
with open("Python Foundations/module 7 File and error handling/Topic 6 Practice/guest_count.txt", "w") as f:
    for num in count:
         f.write(str(num) + "\n")

