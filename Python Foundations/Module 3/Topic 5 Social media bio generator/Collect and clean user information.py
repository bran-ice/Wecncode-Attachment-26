name = input("Enter the users name")
normalised_name = name.strip().title()
profession = input("Enter users profession")
normalised_profession = profession.strip().title()
hobby = input("Enter the users hobby")
normalised_hobby = hobby.strip().lower()
fun_fact = input("Enter users fun fact")
normalised_fun_fact = fun_fact.strip().lower()
print(normalised_name)
print(normalised_profession)
print(normalised_hobby)
print(normalised_fun_fact)

professional_bio = f"My name is, {normalised_name}. I am an {normalised_profession}."
casual_bio = f"I am {normalised_name}, an {normalised_profession} and i like {normalised_hobby}."
creative_bio = f"I am {normalised_name}, an {normalised_profession} but also an {normalised_fun_fact}."
def truncate(bio):
    return bio if len(bio) <= 150 else bio[:147] + "..."

# assume professional_bio, casual_bio, creative_bio are already defined
professional_bio = truncate(professional_bio)
casual_bio = truncate(casual_bio)
creative_bio = truncate(creative_bio)

print(f"1) Professional: {professional_bio}")
print(f"   (chars: {len(professional_bio)})\n")

print(f"2) Casual:       {casual_bio}")
print(f"   (chars: {len(casual_bio)})\n")

print(f"3) Creative:     {creative_bio}")
print(f"   (chars: {len(creative_bio)})\n")

choice = input("Pick a bio by number (1/2/3): ").strip()
if choice == "1":
    print("\nYou picked the Professional bio:\n" + professional_bio)
elif choice == "2":
    print("\nYou picked the Casual bio:\n" + casual_bio)
elif choice == "3":
    print("\nYou picked the Creative bio:\n" + creative_bio)
else:
    print("\nThat's not a valid choice. Please run the program again and pick 1, 2, or 3.")