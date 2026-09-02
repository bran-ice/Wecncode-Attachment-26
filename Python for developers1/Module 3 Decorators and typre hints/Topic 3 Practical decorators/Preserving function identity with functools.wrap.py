from functools import wraps
def my_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print("Before call")
        result = func(*args, **kwargs)
        print("After call")
        return result
    return wrapper

@my_decorator
def greet(name):
    "Return a greeting for name."
    return f"Hello, {name}!"

print(greet("Alice"))
print("name:", greet.__name__)
print("doc:", greet.__doc__)
from functools import wraps

def my_decorator(func):
    def wrapper(*args, **kwargs):
        print("Before call")
        result = func(*args, **kwargs)
        print("After call")
        return result
    return wrapper

@my_decorator
def greet(name):
    "Return a greeting for name."
    return f"Hello, {name}!"

print(greet("Bob"))
print("name:", greet.__name__)
print("doc:", greet.__doc__)
from functools import wraps

registry = []

def my_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print("Before call")
        result = func(*args, **kwargs)
        print("After call")
        return result
    registry.append(wrapper)
    return wrapper

@my_decorator
def greet(name):
    "Return a greeting for name."
    return f"Hello, {name}!"

print(greet("Alice"))
print("name:", greet.__name__)
print("doc:", greet.__doc__)
print("registered:", [p.__name__ for p in registry])