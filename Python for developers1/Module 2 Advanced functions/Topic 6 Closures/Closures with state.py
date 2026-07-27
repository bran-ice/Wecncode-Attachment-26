def make_counter():
    count = [0]
    def increment():
        count[0] += 1
        return count[0]
    return increment

counter = make_counter()
print(counter())
print(counter())
def make_counter():
    count = [0]
    def increment():
        count[0] += 1
        return count[0]
    return increment

a = make_counter()
b = make_counter()

print(a())
print(a())
print(b())
print(a())
print(b())
def make_counter():
    count = [3]
    def increment():
        count[0] += 1
        return count[0]
    return increment

lives = make_counter()
print(lives())
print(lives())