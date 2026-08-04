from functools import wraps
from typing import Callable, Any


def environment_logger(env: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            print(f"[{env}] Executing function: {func.__name__}")
            return func(*args, **kwargs)
        return wrapper
    return decorator


@environment_logger("staging")
def format_transaction(tx_id: str, amount: float) -> str:
    return f"{tx_id}: ${amount:.2f}"


if __name__ == "__main__":
    result = format_transaction("TX123", 45.0)
    print(result)