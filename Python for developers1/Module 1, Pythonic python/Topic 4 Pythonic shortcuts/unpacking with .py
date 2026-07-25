items = [1, 2, 3, 4, 5]
first, *rest = items
print(first)
print(rest)
items = [1, 2, 3, 4, 5]
*start, last = items
print(start)
print(last)

filename = ["mk.jpg", "nk.jpg", "pk.jpg"]
cover, *album = filename
print(cover)
print(album)