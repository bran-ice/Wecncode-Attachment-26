action = print
action("Hello from action")
user_preference = "debug"  
if user_preference == "debug":
    formatter = repr
else:
    formatter = str

value = 123
print(formatter(value))