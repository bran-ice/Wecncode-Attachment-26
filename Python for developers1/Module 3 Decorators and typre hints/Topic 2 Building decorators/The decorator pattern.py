def log_call(func):
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        result = func(*args, **kwargs)
        return result
    return wrapper

@log_call
def area(a, b):
    return a * b

print(area(2, 3))
def log_call(func):
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        result = func(*args, **kwargs)
        return result
    return wrapper

@log_call
def count_items(items):
    return len(items)

print(count_items([1, 2, 3, 4]))