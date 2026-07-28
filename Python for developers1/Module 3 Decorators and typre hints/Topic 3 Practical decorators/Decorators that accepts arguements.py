from functools import wraps

def repeat(times):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = None
            for _ in range(times):
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator

@repeat(3)
def say_hi(name):
    "Return a short greeting."
    print("Running say_hi")
    return f"Hi, {name}!"

print(say_hi("Bob"))
print("name:", say_hi.__name__)
print("doc:", say_hi.__doc__)
from functools import wraps

def repeat(times):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = None
            for _ in range(times):
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator

@repeat(0)
def say_hi(name):
    "Return a short greeting."
    print("Running say_hi")
    return f"Hi, {name}!"

print(say_hi("Bob"))
print("name:", say_hi.__name__)
print("doc:", say_hi.__doc__)
from functools import wraps
def repeat(times):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = None
            for _ in range(times):
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator

record = []

@repeat(3)
def short_message(message):
    print(f"{message}")
    record.append(message)
    return len(record)

print(short_message("server.example.com"))
print(record)