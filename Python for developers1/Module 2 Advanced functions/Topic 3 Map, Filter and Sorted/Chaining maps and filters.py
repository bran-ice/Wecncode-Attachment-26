readings = [0.5, -0.2, 1.3, 2.0, -1.0, 0.0]

positive_cm = list(map(lambda x: x * 100, filter(lambda x: x > 0, readings)))

print("readings:", readings)
print("positive readings in cm:", positive_cm)
readings = [0.5, -0.2, 1.3, 2.0, -1.0, 0.0]

positive_or_zero_cm = list(map(lambda x: x * 100, filter(lambda x: x >= 0, readings)))

print("readings:", readings)
print("positive or zero readings in cm:", positive_or_zero_cm)

counts = ["8", "N/A", "15", " ", "2", "none", "20", "004", "-1"]
numeric_counts = list(map(lambda s: int(s) + 5, filter(lambda s: s.isdigit(), counts)))
print("Original counts:", counts)
print("Numeric counts:", numeric_counts)