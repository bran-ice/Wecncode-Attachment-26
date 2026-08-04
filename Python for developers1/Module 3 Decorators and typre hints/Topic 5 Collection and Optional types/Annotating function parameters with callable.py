from typing import Callable

def apply(func: Callable[[int], str], value: int) -> str:
    return func(value)

def number_to_label(n: int) -> str:
    return f"Number: {n}"

print(apply(number_to_label, 7))
def apply(func: Callable[[int], str], value: int) -> str:
    return func(value)

print(apply(lambda x: f"[{x * 2}]", 5))
from typing import Callable

def format_with(formatter: Callable[[int], str], metric: int) -> str:
    return f"Metric: {formatter(metric)}"

def number_to_text(n: int) -> str:
    return f"{n}"

print(format_with(number_to_text, 1234))
from typing import Callable

def send_metric(maker: Callable[[int], str], payload: int) -> str:
    return "Metric: " + maker(payload)

def to_binary(num: int) -> str:
    return bin(num)

print(send_metric(to_binary, 5))