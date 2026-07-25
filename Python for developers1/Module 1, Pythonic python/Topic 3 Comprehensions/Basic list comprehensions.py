numbers = [1, 2, 3, 4, 5]
squares = [x ** 2 for x in numbers]
print(squares)
numbers = [1, 2, 3, 4, 5]
cubes = [x ** 3 for x in numbers]
print(cubes)

names = ["mirry", "sammy", "nim"]
personalised_greeting = ["Hello," + name + "!" for name in names]
print(personalised_greeting)