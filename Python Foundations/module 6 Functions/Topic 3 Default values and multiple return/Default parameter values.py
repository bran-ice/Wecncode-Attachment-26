def greet(name, greeting="Hello"):
    print(greeting + ", " + name + "!")
    
greet("Alice")
greet("Alice", "Hi")

def greet(name, greeting="Hello"):
    print(greeting + ", " + name + "!")

greet("Bob")
greet(greeting="Good morning", name="Bob")

def message( content, log_level="INFO"):
    print(log_level + ":" + content + ".")

message("Started processing user data")
message(log_level="ERROR", content="Failed to save record")