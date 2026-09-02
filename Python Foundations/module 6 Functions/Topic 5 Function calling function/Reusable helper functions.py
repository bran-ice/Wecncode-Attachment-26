def validate_number(text):
    try:
        num = float(text)
        if num <= 0:
            return None
        return num
    except ValueError:
        return None

def confirm_purchase():
    user = "3"
    qty = validate_number(user)
    print("confirm_purchase qty:", qty)

def quick_add():
    user = "invalid"
    qty = validate_number(user)
    print("quick_add qty:", qty)

if __name__ == "__main__":
    confirm_purchase()
    quick_add()

def validate_number(text):
    try:
        num = float(text)
        if num <= 0:
            return None
        return num
    except ValueError:
        return None

def confirm_purchase():
    user = "0"
    qty = validate_number(user)
    print("confirm_purchase qty:", qty)

def quick_add():
    user = "10"
    qty = validate_number(user)
    print("quick_add qty:", qty)

if __name__ == "__main__":
    confirm_purchase()
    quick_add()

def validate_number(text):
    try: 
        age = int(text)
        if age <= 0:
            return None
        return age
    except ValueError:
        return None

age_text = "12"
age = validate_number(age_text)
if age is None:
    print("Age Invalid:")
else:
    print("Age Accepted:", age)
    
