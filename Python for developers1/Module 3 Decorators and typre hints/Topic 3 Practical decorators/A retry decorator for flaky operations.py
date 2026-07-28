from functools import wraps
def retry(max_attempts):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f"Attempt {attempt} failed: {e}")
                    if attempt == max_attempts:
                        raise
        return wrapper
    return decorator

call_count = {'n': 0}

@retry(4)
def flaky():
    call_count['n'] += 1
    if call_count['n'] < 3:
        raise ValueError("temporary error")
    return "success"

print(flaky())
print("calls:", call_count['n'])
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