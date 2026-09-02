names = ["Benjamin", "Ava", "Li", "Maximillian", "Zoe"]
sorted_by_length = sorted(names, key=lambda name: len(name))
print("original:", names)
print("sorted by length:", sorted_by_length)
names = ["Sam", "Ann", "Bob", "Elizabeth", "Jo"]
sorted_by_length = sorted(names, key=lambda name: len(name))
print(sorted_by_length)

skus = [
    "Q",
    "A1",
    "X9",
    "ZX",
    "M-2",
    "B12C34",
    "PRD-0001",
    "SKU12345",
    "LONGSKU2021",
    "ITEM999999"
]
sorted_by_length = sorted(skus, key=lambda sku: len(sku))
print("Original:", skus)
print("Sorted skus:", sorted_by_length)
