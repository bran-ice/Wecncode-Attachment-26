def add_item_bad(item, basket=[]):
    basket.append(item)
    return basket

print(add_item_bad("apple"))
print(add_item_bad("banana"))

def add_item(item, basket=None):
    if basket is None:
        basket = []
    basket.append(item)
    return basket

print(add_item("apple"))
print(add_item("banana"))
def add_item_bad(item, basket=[]):
    basket.append(item)
    return basket

print(add_item_bad("apple"))
print(add_item_bad("banana", []))
print(add_item_bad("cherry"))
def add_header(key, value, headers=None):
    if headers is None:
        headers = {}
    headers[key] = value
    return headers

print(add_header("Accept", "application/json"))
print(add_header("User-Agent", "MyApp/2.0", {}))
print(add_header("Authorization", "Bearer xyz"))