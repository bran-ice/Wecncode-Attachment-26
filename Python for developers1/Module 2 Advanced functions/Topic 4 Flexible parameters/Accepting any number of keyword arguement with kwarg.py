def print_info(**kwargs):
    for key, value in kwargs.items():
        print(f"{key}: {value}")

print_info(name="Alice", age=30, city="Seattle")
def print_info(**kwargs):
    print("Received", len(kwargs), "fields")
    for key, value in kwargs.items():
        print(f"{key}: {value}")

print_info(country="Canada")
def build_query(**kwargs):
    parts = []
    for key, value in kwargs.items():
        parts.append(f"{key}={value}")
    return "&".join(parts)

print(build_query(search="python", page=2, sort="recent"))
def make_profile(**kwargs):
    profile = {}
    for key, value in kwargs.items():
        profile[key] = value
    return profile

print(make_profile(username="coder", active=True, followers=120))
def build_system(**kwargs):
    count = len(kwargs)
    names = ", ".join(kwargs.keys())
    return f"Received {count} fields: {names}"

print(build_system(frequency="weekly", topics="python", format="HTML"))