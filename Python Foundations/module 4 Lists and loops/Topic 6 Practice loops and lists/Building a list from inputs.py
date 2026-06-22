fruits = []
while True:
    fruit = input("enter the fruits name(enter done to stop)")
    if fruit == "done":
        break
    fruits.append(fruit)
print(len(fruits))
print(fruits)
    