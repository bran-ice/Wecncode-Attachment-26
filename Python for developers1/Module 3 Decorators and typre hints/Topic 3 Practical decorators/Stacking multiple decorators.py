from functools import wraps

def timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print("TIMER: start")
        result = func(*args, **kwargs)
        print("TIMER: end")
        return result
    return wrapper

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

@timer
@repeat(2)
def greet(name):
    print(f"Hello, {name}!")
    return "greeted"

print(greet("Ava"))
print("function name:", greet.__name__)
def timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print("TIMER: start")
        result = func(*args, **kwargs)
        print("TIMER: end")
        return result
    return wrapper

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

@repeat(2)
@timer
def greet(name):
    print(f"Hello, {name}!")
    return "greeted"

print(greet("Ava"))
print("function name:", greet.__name__)

from functools import wraps
counts = []
def timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print("TIMER: start")
        result = func(*args, **kwargs)
        print("TIMER: end")
        return result
    return wrapper

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

@timer
@repeat(3)
def batch_task():
    print("running task")
    counts.append(1)
    return len(counts)

print(batch_task())
print(counts)