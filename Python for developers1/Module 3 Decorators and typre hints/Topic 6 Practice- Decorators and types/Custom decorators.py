from functools import wraps
def parcelpro_diagnostics(func):
    call_count = 0
    @wraps(func)
    def wrapper(*args, **kwargs):
      nonlocal call_count
      call_count += 1
      print(
        f"[ParcelPro] Calling {func.__name__} with args: {args} kwargs: {kwargs}"
    )
      result = func(*args, **kwargs)
      print(result)
      print(f"[ParcelPro] {func.__name__} has been called {call_count} time(s)\n")

      return result

    return wrapper


@parcelpro_diagnostics
def calculate_shipping(weight, destination="NY"):
  cost = weight * 4.00 if destination == "NY" else weight * 5.00
  return f"Shipping cost: {cost:.2f}"


@parcelpro_diagnostics
def apply_discount(price, percentage):
  discounted = price * (1 - percentage / 100)
  return f"Discounted price: {discounted:.2f}"

if __name__ == "__main__":
  calculate_shipping(3, destination="NY")
  apply_discount(150.0, 10)
  calculate_shipping(1, destination="CA")