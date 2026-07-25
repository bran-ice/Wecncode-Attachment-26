animals = ["Cat", "dog", "owl", "Horse", "bee"]
short_caps = [a.upper() for a in animals if len(a) <= 3]
print(short_caps)