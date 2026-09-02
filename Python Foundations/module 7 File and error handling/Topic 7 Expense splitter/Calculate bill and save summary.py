# 1. Calculate subtotal
subtotal = 0
for item in items:
    subtotal = subtotal + item["price"]

# 2. Get inputs with defaults
try:
    tip_percent = int(input("Enter the tip percentage: "))
except ValueError:
    tip_percent = 0

try:
    people_input = int(input("Enter the number of people: "))
    if people_input <= 0:
        people_input = 1
except ValueError:
    people_input = 1

# 3. Calculations
tip_amount = subtotal * (tip_percent / 100)
grand_total = subtotal + tip_amount
per_person = grand_total / people_input

# 4. Generate the formatted summary using "{:.2f}".format()
summary_text = "--- Receipt Summary ---\n"
for item in items:
    summary_text += item['name'] + " $" + "{:.2f}".format(item['price']) + "\n"
summary_text += "-------------------------\n"
summary_text += "Subtotal: $" + "{:.2f}".format(subtotal) + "\n"
summary_text += "Tip (" + str(tip_percent) + "%): $" + "{:.2f}".format(tip_amount) + "\n"
summary_text += "Grand Total: $" + "{:.2f}".format(grand_total) + "\n"
summary_text += "-------------------------\n"
summary_text += "People: " + str(people_input) + "\n"
summary_text += "Each pays: $" + "{:.2f}".format(per_person) + "\n"

# 5. Print and Save
print("\n" + summary_text)

summary_path = "Python Foundations/module 7 File and error handling/Topic 7 Expense splitter/split_summary.txt"
with open(summary_path, "w") as f:
    f.write(summary_text)

print("\nConfirmation: Summary saved to '" + summary_path + "'")