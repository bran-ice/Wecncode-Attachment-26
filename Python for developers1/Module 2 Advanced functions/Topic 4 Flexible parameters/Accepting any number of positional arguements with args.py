def total(*args):
    return sum(args)

print(total(10, 5, 3))
print(total(1, 2, 3, 4, 5))
print(total())
def total(*args):
    print(args)
    print(len(args))
    return sum(args)

print(total(7, 3))
print(total())

def summarize(*args):
    return (sum(args), len(args))

print(summarize(4, 3))