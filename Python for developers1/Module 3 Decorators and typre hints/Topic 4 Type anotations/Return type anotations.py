def calculate_total(price: float, quantity: int) -> float:
    total = price * quantity
    return total

print(calculate_total(12.5, 3))
def show_total(price: float, quantity: int) -> None:
    print("Total:", price * quantity)

show_total(12.5, 3)
def calculate_total_int(price: float, quantity: int) -> int:
    return price * quantity

print(calculate_total_int(12.5, 3))
def username_validator(username: str) -> bool:
    return len(username) >= 3 and username.isalnum()

print(username_validator("Branice"))
print(username_validator("Ndalu"))
print(username_validator("A!"))
print(username_validator("ab"))
