def get_rate(state):
    if state == "CA":
        return 0.0825
    if state == "NY":
        return 0.04
    return 0.05

def calculate_tax(amount, state):
    rate = get_rate(state)
    return amount * rate

def calculate_total(amount, state):
    tax = calculate_tax(amount, state)
    return amount + tax

if __name__ == "__main__":
    subtotal = 100.00
    state = "CA"
    print("Subtotal:", subtotal)
    print("Tax:", calculate_tax(subtotal, state))
    print("Total:", calculate_total(subtotal, state))

def get_rate(state):
    if state == "CA":
        return 0.0825
    if state == "NY":
        return 0.04
    return 0.05

def calculate_tax(amount, state):
    rate = get_rate(state)
    return amount * rate

def calculate_total(amount, state):
    tax = calculate_tax(amount, state)
    return amount + tax

if __name__ == "__main__":
    subtotal = 11.49
    state = "OR"
    print("Subtotal:", subtotal)
    print("Tax:", calculate_tax(subtotal, state))
    print("Total:", calculate_total(subtotal, state))