mode = "production"

def set_mode_local():
    mode = "debug"          # assignment creates a local variable named `mode`
    print("inside set_mode_local:", mode)

set_mode_local()
print("outside after set_mode_local:", mode)

mode = "production"

def set_mode_global():
    global mode            # tell Python: use the module-level `mode`
    mode = "debug"
    print("inside set_mode_global:", mode)

set_mode_global()
print("outside after set_mode_global:", mode)

greeting = "en"

def print_greeting():
    if greeting == "en":
        print("Hello")
    elif greeting == "es":
        print("Hola")
    else:
        print("Hello (unknown language)", greeting)

def set_greeting_global(new_lang):
    global greeting
    greeting = new_lang
    print("inside set_greeting_global:", greeting)

print_greeting()
set_greeting_global("es")
print_greeting()