from typing import Callable

def apply(func: Callable[[int], str], value: int) -> str:
    return func(value)

def number_to_label(n: int) -> str:
    return f"Number: {n}"

print(apply(number_to_label, 7))
def apply(func: Callable[[int], str], value: int) -> str:
    return func(value)

print(apply(lambda x: f"[{x * 2}]", 5))