def set_age(age):
    if age < 0:
        raise ValueError("Age cannot be negative")
    print("Age accepted:", age)

def valid_network(port_number):
    if port_number < 1 or port_number > 65535:
       raise ValueError("out of range")
    print("Port number confirmed:", port_number)
valid_network(22250)