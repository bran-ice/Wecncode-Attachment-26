def apply_twice(func, value):
    return func(func(value))

result = apply_twice(lambda x: x + 1, 5)
print(result)
def apply_twice(func, value):
    return func(func(value))

result = apply_twice(lambda x: x * 2, 3)
print(result)
def apply_twice(func, value):
    return func(func(value))
current_title = "title"
result = apply_twice(lambda s: "**" + s + "**", "Chapter 1")
print(result)