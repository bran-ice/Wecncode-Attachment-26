def set_age(age):
    if age <= 0:
        raise ValueError("Age must be positive")
    print("Age accepted:", age)

set_age(25)
def set_password(password):
    if len(password) <= 5:
        raise ValueError("too short")
    print("accepted")
set_password("mymonicah1")