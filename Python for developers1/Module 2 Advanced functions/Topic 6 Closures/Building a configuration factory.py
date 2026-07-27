def make_multiplier(factor):
    def multiply(x):
        return x * factor
    return multiply

double = make_multiplier(2)
triple = make_multiplier(3)

print(double(5))
print(triple(4))
def make_multiplier(factor):
    return lambda x: x * factor

double = make_multiplier(2)
times_ten = make_multiplier(10)

print(double(6))
print(times_ten(3))
def make_calibrator(temperature):
    return lambda x: x * temperature
sensorA_reading = make_calibrator(0.98)
sensorB_reading = make_calibrator(1.05)
print(sensorA_reading(23))
print(sensorB_reading(33))