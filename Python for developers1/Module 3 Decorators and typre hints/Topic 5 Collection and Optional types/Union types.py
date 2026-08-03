def lookup(key: str | int) -> str:
    records = {"alice": "Alice Smith", 42: "The Answer"}
    return records.get(key, "Not found")

print(lookup("alice"))
print(lookup(42))
print(lookup("missing"))
def make_greeting(name: str | list[str]) -> str:
    if isinstance(name, str):
        person = name
    else:
        names = name
        if len(names) == 0:
            person = ""
        elif len(names) == 1:
            person = names[0]
        elif len(names) == 2:
            person = f"{names[0]} and {names[1]}"
        else:
            person = ", ".join(names[:-1]) + ", and " + names[-1]
    if person:
        return f"Welcome, {person}!"
    else:
        return "Welcome!"