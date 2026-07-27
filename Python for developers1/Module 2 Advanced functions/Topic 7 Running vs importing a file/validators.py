print("__name__ at top of validators.py ->", __name__)

def is_valid_email(s):
    return "@" in s

def is_strong_password(s):
    return len(s) >= 8

if __name__ == "__main__":
    print("Running validators.py directly: manual tests")
    print(is_valid_email("me@example.com"))
    print(is_strong_password("P@ssw0rd"))