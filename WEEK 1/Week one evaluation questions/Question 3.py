name = input("what is the employees name?")
rate = float(input("Input employees hourly rate"))
hours = float(input("Input hours per week"))
bonus = input("Is the employee a manager?(yes/no)")
normalised_bonus = bonus.strip().lower()

if hours <= 40:
    gross = rate * hours
else:
    gross = rate * 40 + (hours-40) * rate * 1.5

if normalised_bonus == "yes" and gross >= 20000:
    gross += 2000
if gross < 15000:
    tax = 0
elif gross < 30000:
     tax = 0.1 * gross
else:
    tax = 0.2 * gross

net = gross - tax
print("Employee:" , name)
print(f"Gross Pay: ${gross}")
print(f"Net Pay: ${net}")