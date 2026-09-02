import time

def timer(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"Elapsed: {end - start} seconds")
        return result
    return wrapper

@timer
def greet(name):
    return f"Hello, {name}!"

print(greet("Alice"))
import time

def timer(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"Elapsed: {end - start} seconds")
        return result
    return wrapper

@timer
def slow_task():
    time.sleep(0.5)
    return "Done"

print(slow_task())
def timer(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"Elapsed: {end - start} seconds")
        return result
    return wrapper

@timer
def sort_numbers(numbers):
    return sorted(numbers)

nums = list(range(100000, 0, -1))
print(sort_numbers(nums)[:5])

import time
def timer(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"Elapsed: {end - start} seconds")
        return result
    return wrapper

@timer
def make_squares(n):
    squares = []
    for i in range(n):
        squares.append(i * i)
    return squares

print(len(make_squares(100000)))