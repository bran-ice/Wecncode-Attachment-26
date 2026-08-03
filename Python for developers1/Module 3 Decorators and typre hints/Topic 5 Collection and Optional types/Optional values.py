name: str | None = None
print(name)
name = "Alice"
print(name)
def find_user(email: str) -> dict | None:
    users = {"a@example.com": {"name": "Ann"}, "b@example.com": {"name": "Bob"}}
    return users.get(email)

print(find_user("a@example.com"))
print(find_user("unknown@example.com"))
def get_name(user: dict | None) -> str | None:
    if user is None:
        return None
    return user.get("name")

print(get_name({"name": "Ann"}))
print(get_name(None))
def format_contact(name: str, phone: str | None = None) -> str:
    if phone is None:
        return name
    return f"{name} ({phone})"
print(format_contact("Branice", "0743"))
print(format_contact("Branice", None))