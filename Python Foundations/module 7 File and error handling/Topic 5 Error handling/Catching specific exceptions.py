filename = input("Enter the filename: ")
config_key = input("Enter the configuration key: ")

try:
    f = open(filename)
    value = f.readline().strip()
    f.close()

    count = int(value)

    settings = {"timeout": 30, "threads": 4, "path": "/data"}
    config_value = settings[config_key]

    print(f"Count: {count}, Config: {config_value}")
except FileNotFoundError:
    print(f"File '{filename}' not found.")
except ValueError:
    print("The first line is not a valid integer.")
except KeyError:
    print(f"Configuration key '{config_key}' not found.")
