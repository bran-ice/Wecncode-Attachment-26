operations = {
    "add": lambda a, b: a + b,
    "multiply": lambda a, b: a * b
}

print(operations["add"](3, 5))
print(operations["multiply"](4, 6))

conversion = {
    "m to cm": lambda a: a * 100,
     "cm to m": lambda b: b / 100
}
print(conversion["m to cm"](3.5))
print(conversion["cm to m"](250))