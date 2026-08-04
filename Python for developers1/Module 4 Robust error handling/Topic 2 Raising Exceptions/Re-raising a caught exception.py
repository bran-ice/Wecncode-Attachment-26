def set_age(age):
    if age < 0:
        raise ValueError("Age cannot be negative")
    print("Age accepted:", age)

try:
    set_age(5)
except ValueError as e:
    print(f"Warning: {e}")
    raise
def set_age(age):
    if age < 0:
        raise ValueError("Age cannot be negative")
    print("Age accepted:", age)

def caller():
    try:
        set_age(-5)
    except ValueError as e:
        print(f"Warning inside caller: {e}")
        raise

caller()

def config_file(timeout_text):
    value = int(timeout_text)
    if value < 1 or value > 300:
      raise ValueError("timeout out of range")
    print("In range:", timeout_text)
    return value
def caller(section_name, timeout_text):
    try:
        value = config_file(timeout_text)
        print("Using timeout:", value)
    except ValueError as e:
        print(f"Warning: section {section_name}: {e}")
        raise

caller("network", "77")
caller("network", "eight")