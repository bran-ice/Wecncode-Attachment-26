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

