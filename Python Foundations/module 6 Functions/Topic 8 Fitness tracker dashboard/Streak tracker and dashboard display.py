def process_streak(workout_days):
    count = len(workout_days)
    if count <= 1:
        message = "Just getting started! Keep building that momentum."
    elif 2 <= count <= 3:
        message = "Great consistency! You're making real progress."
    else:
        message = "Incredible dedication! You are unstoppable."
    return count, message

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

def calculate_calories(weight_kg, height_cm, age, activity_level):
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    factors = {"sedentary": 1.2, "moderate": 1.55, "very": 1.9}
    factor = factors.get(activity_level, 1.2) # Defaults to sedentary
    return base * factor

def main():
    # Gather inputs
    weight = float(input("Weight (kg): "))
    height_cm = float(input("Height (cm): "))
    age = int(input("Age (years): "))
    activity = input("Activity level (sedentary/moderate/very): ").strip().lower()
    
    workout_days = []
    print("Enter the names of days you worked out (or 'done' to finish):")
    while True:
        day = input("> ").strip()
        if day.lower() == 'done': break
        if day: workout_days.append(day)
    
    # Process calculations
    bmi_val, bmi_cat = calculate_bmi(weight, height_cm / 100)
    cal_target = calculate_calories(weight, height_cm, age, activity)
    streak_count, streak_msg = process_streak(workout_days)
    
    # Produce the dashboard
    print("\n" + "="*40)
    print("           FITNESS DASHBOARD           ")
    print("="*40)
    print(f"BMI: {bmi_val:.1f} ({bmi_cat})")
    print("-"*40)
    print(f"Daily Calorie Target: {cal_target:.0f} kcal")
    print("-"*40)
    print(f"Streak: {streak_count} days - {streak_msg}")
    print("="*40)

if __name__ == "__main__":
    main()