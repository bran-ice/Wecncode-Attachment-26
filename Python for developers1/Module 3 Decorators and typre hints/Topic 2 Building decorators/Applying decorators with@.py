def log_call(func):
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper

def greet(name):
    return f"Hello, {name}!"

greet = log_call(greet)   # apply decorator by assignment
print(greet("Alice"))
def log_call(func):
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper

@log_call
def is_even(n):
    return n % 2 == 0

print(is_even(4))
print(is_even(5))
def log_call(func):
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper

@log_call
def names(a, b):
    return f"{a} {b}"

print(names("Branice", "Nafula"))