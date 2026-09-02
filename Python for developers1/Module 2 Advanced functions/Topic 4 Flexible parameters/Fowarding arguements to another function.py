def greet(greeting, name, punctuation="."):
    return f"{greeting}, {name}{punctuation}"

def wrapper(*args, **kwargs):
    print("Wrapper received args:", args)
    print("Wrapper received kwargs:", kwargs)
    return greet(*args, **kwargs)

print(wrapper("Hello", "Eve", punctuation="!"))
def greet(greeting, name, punctuation="."):
    return f"{greeting}, {name}{punctuation}"

def wrapper(*args, **kwargs):
    print("Before forwarding, args:", args)
    print("Before forwarding, kwargs:", kwargs)
    result = greet(*args, **kwargs)
    print("Result from greet:", result)
    return result

print(wrapper("Hi", name="Sam"))
def request_handler(method, path, user_info, headers):
    return f"{method}, {path}, {user_info}, {headers}"
def wrapper(*args, **kwargs):
    print("Before fowarding, args:", args)
    print("Before fowarding, kwargs:", kwargs)
    result = request_handler(*args, **kwargs)
    return result
print(wrapper(method = "POST", path = "/api/users/123/profile", user_info = {"id": 123, "username": "alice", "role": "admin", "authenticated": True}, headers = {
    "User-Agent": "MyApp/1.0"}))
