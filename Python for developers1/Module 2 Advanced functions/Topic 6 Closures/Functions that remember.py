def make_greeter(greeting):
    def greeter(name):
        print(greeting + ", " + name)
    return greeter

hello_greeter = make_greeter("Hello")
hello_greeter("Alice")
def make_greeter(greeting):
    def greeter(name):
        print(greeting + ", " + name)
    return greeter

hello = make_greeter("Hello")
hola = make_greeter("Hola")

hello("Alice")
hola("Carlos")
def currency_formatter(currency):
    def formatter(amount):
        print(currency + str(amount))
    return formatter

usd = currency_formatter("$")
eur = currency_formatter("€")

usd(10)
eur(5.5)


                  