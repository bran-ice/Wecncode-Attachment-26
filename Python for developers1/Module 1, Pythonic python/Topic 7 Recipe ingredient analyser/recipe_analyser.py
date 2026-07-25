recipe1 = {"Papprika": "two", "Garlic": "three", "Ginger": "one", "Masala": "two", "Chilli": "three", "Turmeric": "two"}
recipe2 = {"Masala": "one", "salt": "one", "cheese": "two", "Garlic": "two", "Cardamon": "one", "Chilli": "one"}
allegen_set = {"Papprika", "Masala", "Peanuts", "Milk"}
recipe1_keys = set(recipe1.keys())
recipe2_keys = set(recipe2.keys())

ingredientin_both = recipe1_keys & recipe2_keys
recipe1_only = recipe1_keys - recipe2_keys
recipe2_only = recipe2_keys - recipe1_keys
combined_recipes = recipe1_keys  | recipe2_keys

print(f"Ingredients in both: {ingredientin_both}")
print(f"Ingredients in recipe 1 only: {recipe1_only}")
print(f"Ingredients in recipe 2 only: {recipe2_only}")
print(f"Combined ingredients: {combined_recipes}")
all_recipes = {**recipe1, **recipe2}
shopping_list = {ingredient: all_recipes[ingredient] for ingredient in combined_recipes}
display_list = [f"[ALLERGEN] {ingredient}: {shopping_list[ingredient]}" if ingredient in allegen_set else f"{ingredient}: {shopping_list[ingredient]}" for ingredient in combined_recipes]
for index, item in enumerate(display_list, start=1):
    print(f"{index}. {item}")