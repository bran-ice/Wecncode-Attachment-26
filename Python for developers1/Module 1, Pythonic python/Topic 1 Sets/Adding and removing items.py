colors = {"red", "blue", "green"}
colors.add("yellow")
print(colors)

colors.remove("red")
print(colors)

colors.discard("purple")
print(colors)

colors = {"red", "blue"}
colors.add("blue")
print(colors)

colors.discard("green")
print(colors)

colors.remove("green")
print("This line will not run if remove() raises an error")