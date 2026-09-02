def export_prompts(prompts):
    print("Export Options:")
    print("1. All prompts")
    print("2. Favorites only")
    print("3. By category")
    
    choice = input("Enter your choice: ")
    to_export = []
    
    if choice == "1":
        to_export = prompts
    elif choice == "2":
        to_export = [p for p in prompts if p["favorite"]]
    elif choice == "3":
        categories = list(set(p["category"] for p in prompts))
        for i, cat in enumerate(categories, 1):
            print(f"{i}. {cat}")
        cat_choice = int(input("Select category number: ")) - 1
        selected_cat = categories[cat_choice]
        to_export = [p for p in prompts if p["category"] == selected_cat]
    else:
        print("Invalid choice.")
        return

    filename = input("Enter output filename")
    try:
        with open(filename, "w") as f:
            for p in to_export:
                f.write(f"Title: {p['title']}\n")
                f.write(f"Prompt: {p['prompt']}\n")
                f.write(f"Category: {p['category']}\n")
                f.write(f"Tags: {','.join(p['tags'])}\n")
                f.write(f"Favorite: {p['favorite']}\n")
                f.write("-" * 20 + "\n")
        print(f"Successfully exported {len(to_export)} prompts to {filename}.")
    except Exception as e:
        print(f"Error exporting file: {e}")