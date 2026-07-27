print("utils.py loaded. __name__ ->", __name__)

def greet(name):
    print("Hello,", name)

if __name__ == "__main__":
    greet("Alice")