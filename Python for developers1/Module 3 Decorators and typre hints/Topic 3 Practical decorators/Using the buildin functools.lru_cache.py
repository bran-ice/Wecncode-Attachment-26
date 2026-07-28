import time
from functools import lru_cache

@lru_cache(maxsize=128)
def get_user(user_id):
    print("looking up user", user_id)
    time.sleep(1)  # simulate slow work
    return {"id": user_id, "name": f"User{user_id}"}

print(get_user(1))
print(get_user(1))
print(get_user(2))
print(get_user(1))
@lru_cache(maxsize=2)
def get_user(user_id):
    print("looking up user", user_id)
    time.sleep(1)
    return {"id": user_id, "name": f"User{user_id}"}

print(get_user(1))
print(get_user(2))
print(get_user(1))
print(get_user(3))
print(get_user(2))

import time
from functools import lru_cache
@lru_cache(maxsize=6)
def convert_currency(currency):
    print("converting currency", currency)
    time.sleep(1)  # simulate slow rendering
    return f"Report-{currency}"

print(convert_currency("USD"))
print(convert_currency("EUR"))
print(convert_currency("USD"))