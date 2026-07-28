from functools import wraps
def memoize(func):
    cache = {}
    @wraps(func)
    def wrapper(*args):
        if args in cache:
            print("cache hit for", args)
            return cache[args]
        print("cache miss for", args)
        result = func(*args)
        cache[args] = result
        return result
    return wrapper

@memoize
def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)

print("fib(6) =", fib(6))
print("fib(6) again =", fib(6))
def memoize(func):
    cache = {}
    def wrapper(*args):
        if args in cache:
            print("cache hit for", args)
            return cache[args]
        print("cache miss for", args)
        result = func(*args)
        cache[args] = result
        return result
    return wrapper

@memoize
def square(x):
    print("computing square for", x)
    return x * x

print("A:", square(3))
print("B:", square(3))
print("C:", square(4))
print("D:", square(3))
def memoize(func):
    cache = {}
    def wrapper(*args):
        if args in cache:
            print("cache hit for", args)
            return cache[args]
        print("cache miss for", args)
        result = func(*args)
        cache[args] = result
        return result
    return wrapper

@memoize
def distance(x1, y1, x2, y2):
    print("computing distance for", (x1, y1, x2, y2))
    dx = x2 - x1
    dy = y2 - y1
    return (dx * dx + dy * dy) ** 0.5

print(distance(0, 0, 3, 4))
print(distance(0, 0, 3, 4))
print(distance(1, 1, 4, 5))
print(distance(0, 0, 3, 4))

import time

def memoize(func):
    cache = {}
    def wrapper(*args):
        if args in cache:
            print("cache hit for", args)
            return cache[args]
        print("cache miss for", args)
        result = func(*args)
        cache[args] = result
        return result
    return wrapper

@memoize
def get_user(user_id):
    print("looking up user", user_id)
    time.sleep(1)  # simulate slow work
    return {"id": user_id, "name": f"User{user_id}"}

print(get_user(1))
print(get_user(1))
print(get_user(2))
print(get_user(1))