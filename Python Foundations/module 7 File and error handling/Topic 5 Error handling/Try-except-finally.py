text = input("Enter a short note: ")
f = None
try:
    f = open("notes.txt", "a")
    f.write ("text\n")
except Exception:
    print("Could not save note")
finally:
    if f:
        f.close()
    print("Save complete")