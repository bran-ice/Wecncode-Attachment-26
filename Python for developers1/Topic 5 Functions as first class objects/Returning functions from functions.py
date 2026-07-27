def make_greeter(greeting):
    def greet(name):
        return f"{greeting}, {name}!"
    return greet

hello = make_greeter("Hello")
print(hello("Alice"))
def make_greeter(greeting):
    def greet(name):
        return f"{greeting}, {name}!"
    return greet

hi = make_greeter("Hi")
welcome = make_greeter("Welcome")

print(hi("Sam"))
print(welcome("Sam"))
def make_repeater(time):
    def repeat(ha):
        return ha * time
    return repeat
repeater2 = make_repeater(2)
print(repeater2("ha"))
repeater3 = make_repeater(3)
print(repeater3("ha"))
