from functools import wraps
from typing import Callable, Any, Dict, Tuple
import random
import time


def timer(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    def wrapper(*args: object, **kwargs: object) -> Any:
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"[{func.__name__}] Executed in {end_time - start_time:.4f} seconds")
        return result
    return wrapper


def retry(max_attempts: int) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: object, **kwargs: object) -> Any:
            attempts = 0
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    if attempts >= max_attempts:
                        raise e
            raise RuntimeError(f"Failed after {max_attempts} attempts")
        return wrapper
    return decorator


def memoize(func: Callable[..., Any]) -> Callable[..., Any]:
    cache: Dict[Tuple[Any, ...], Any] = {}

    @wraps(func)
    def wrapper(*args: object, **kwargs: object) -> Any:
        key = (args, tuple(sorted(kwargs.items())))
        if key in cache:
            return cache[key]
        result = func(*args, **kwargs)
        cache[key] = result
        return result
    return wrapper


def call_counter(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    def wrapper(*args: object, **kwargs: object) -> Any:
        wrapper.calls += 1
        print(f"[{func.__name__}] Call count: {wrapper.calls}")
        return func(*args, **kwargs)
    
    wrapper.calls = 0
    return wrapper

@retry(max_attempts=5)
@call_counter

def unreliable_api_call(endpoint: str) -> str:
    if random.choice([True, False]):
        raise ConnectionError("Network timeout while connecting to server")
    return f"Successfully fetched data from {endpoint}"


@timer
@memoize
def fibonacci(n: int) -> int:
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


@timer
@call_counter
def process_data(items: list) -> int:
    time.sleep(0.05)
    return len(items)


if __name__ == "__main__":
    print("=== RELIABILITY & DECORATOR SUITE REPORT ===\n")

    print("--- 1. Testing Unreliable Function with @retry and @call_counter ---")
    retry_status = "Failed"
    try:
        api_result = unreliable_api_call("https://api.parcelpro.com/v1/status")
        retry_status = f"Success: '{api_result}'"
    except ConnectionError as err:
        retry_status = f"Failed after max attempts ({err})"
    
    print(f"Outcome: {retry_status}")
    print(f"Total Call Attempts Executed: {unreliable_api_call.calls}\n")

    print("--- 2. Testing Fibonacci with @timer and @memoize ---")
    fib_val_1 = fibonacci(10)
    fib_val_2 = fibonacci(10)
    
    print(f"Result for fibonacci(10): {fib_val_1}")
    print(f"Cache Effectiveness: Second call was served instantly via @memoize.\n")

    print("--- 3. Testing Data Processor with @timer and @call_counter ---")
    data = [1, 2, 3, 4, 5]
    processed_count_1 = process_data(data)
    processed_count_2 = process_data(data)
    
    print(f"Processed item count: {processed_count_1}")
    print(f"Total Call Count: {process_data.calls}\n")

    print("=== FINAL EXECUTION SUMMARY ===")
    print(f"• Unreliable API Retry Status: {retry_status}")
    print(f"• Unreliable API Call Count:  {unreliable_api_call.calls}")
    print(f"• Fibonacci(10) Value:         {fib_val_1}")
    print(f"• Process Data Invocation Count: {process_data.calls}")