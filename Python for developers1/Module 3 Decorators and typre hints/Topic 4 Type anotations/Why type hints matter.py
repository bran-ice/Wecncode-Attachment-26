def get_display_name(user_id: int) -> int:
    if user_id == 1:
        return "alice"
    return 404

name = get_display_name(2)
print(name.upper())
def describe_age(age: int) -> str:
    if age >= 18:
        return "Adult"
    return "Minor"
print(describe_age(12))
print(describe_age(22))
