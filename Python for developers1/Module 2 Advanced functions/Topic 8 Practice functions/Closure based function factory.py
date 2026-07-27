def make_fare_calculator(multiplier):
    return lambda base_fare: base_fare * multiplier

member_calculator = make_fare_calculator(0.9)
last_minute_calculator = make_fare_calculator(1.25)

member_fare = member_calculator(150.0)
last_minute_fare = last_minute_calculator(300.0)

print(f"Member fare for 150.0: {member_fare}")
print(f"Last-minute fare for 300.0: {last_minute_fare}")