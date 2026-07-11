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

def process_streak(workout_days):
    """
    Accepts the list of workout days, calculates the count, 
    and returns both the count and the appropriate message.
    """
    count = len(workout_days)
    
    # Message thresholds based on count
    if count < 3:
        message = "Just getting started! Keep building that momentum."
    elif 3 <= count <= 6:
        message = "Great consistency! You're making real progress."
    else:
        message = "Incredible dedication! You are unstoppable."
        
    return count, message

def main():
    # Gather input with a while loop
    workout_days = []
    print("Enter the names of days you worked out (or type 'done' to finish):")
    
    while True:
        day = input("> ").strip()
        if day.lower() == 'done':
            break
        if day:
            workout_days.append(day)
    
    # Static metrics for the dashboard
    bmi = 22.5
    bmi_category = "Normal"
    calorie_target = 2200
    
    # Process streak using the updated function
    streak_count, streak_message = process_streak(workout_days)
    
    # Produce the dashboard
    print("\n" + "="*30)
    print("      FITNESS DASHBOARD")
    print("="*30)
    
    print(f"BMI: {bmi} ({bmi_category})")
    print("-"*30)
    print(f"Calorie Target: {calorie_target} kcal")
    print("-"*30)
    print(f"Streak: {streak_count} days - {streak_message}")
    print("="*30)

if __name__ == "__main__":
    main()



