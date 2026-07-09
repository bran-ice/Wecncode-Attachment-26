#calculating bmi
def calculate_bmi(weight_kg, height_m):
    bmi = weight_kg / (height_m ** 2)
    if bmi < 18.5:
        category = "Underweight"
    elif bmi < 25:
        category = "Normal"
    elif bmi < 30:
        category = "Overweight"
    else:
        category = "Obese"
    return bmi, category

weight = float(input("Weight (kg): "))
height_cm = float(input("Height (cm): "))
height_m = height_cm / 100
age = int(input("Age (years): "))
activity = input("Activity level (sedentary/moderate/very): ").strip().lower()

bmi_value, bmi_category = calculate_bmi(weight, height_m)
print(f"BMI: {bmi_value:.1f}, Category: {bmi_category}")

#calories calculations
def daily_calories(weight_kg, height_cm, age, activity_level):
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    if activity_level == "sedentary":
        factor = 1.2
    elif activity_level == "moderate":
        factor = 1.55
    elif activity_level == "very":
        factor = 1.9
    else:
        raise ValueError("activity_level must be 'sedentary', 'moderate', or 'very'")
    return base * factor


cal_target = daily_calories(weight, height_cm, age, activity)
print(f"Daily calorie target: {cal_target:.0f} kcal")