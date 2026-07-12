def save_to_csv(prompts, filename="prompts.csv"):
    with open(filename, "w") as f:
        f.write("title|prompt|category|tags|favorite\n")
        for p in prompts:
            fav = "1" if p["favorite"] else "0"
            tags_str = ",".join(p["tags"])
            line = f"{p['title']}|{p['prompt']}|{p['category']}|{tags_str}|{fav}\n"
            f.write(line)

def toggle_favorite(prompts):
    for index, p in enumerate(prompts, 1):
        status = "[Favorite]" if p["favorite"] else "[Unmarked]"
        print(f"{index}. {p['title']} {status}")
    
    choice = input("Select a number to toggle favorite: ")
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(prompts):
            prompts[idx]["favorite"] = not prompts[idx]["favorite"]
            save_to_csv(prompts)
            print("Favorite status updated.")
        else:
            print("Invalid selection.")
    except ValueError:
        print("Invalid input.")

def edit_prompt(prompts):
    for index, p in enumerate(prompts, 1):
        print(f"{index}. {p['title']}")
    
    choice = input("Select a number to edit: ")
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(prompts):
            p = prompts[idx]
            print(f"\nEditing: {p['title']}")
            print(f"Current values: Title: {p['title']}, Prompt: {p['prompt']}, Category: {p['category']}, Tags: {','.join(p['tags'])}, Favorite: {p['favorite']}")
            
            new_title = input(f"New title (Enter to keep '{p['title']}'): ")
            if new_title: p["title"] = new_title
            
            new_text = input(f"New text (Enter to keep current): ")
            if new_text: p["prompt"] = new_text
            
            new_cat = input(f"New category (Enter to keep '{p['category']}'): ")
            if new_cat: p["category"] = new_cat
            
            new_tags = input(f"New tags (comma-separated, Enter to keep '{','.join(p['tags'])}'): ")
            if new_tags: p["tags"] = new_tags.split(",")
            
            new_fav = input(f"Set as favorite? (y/n, Enter to keep '{p['favorite']}'): ")
            if new_fav.lower() == 'y': p["favorite"] = True
            elif new_fav.lower() == 'n': p["favorite"] = False
                
            save_to_csv(prompts)
            print("Prompt updated successfully.")
        else:
            print("Invalid selection.")
    except ValueError:
        print("Invalid input.")

def delete_prompt(prompts):
    for index, p in enumerate(prompts, 1):
        print(f"{index}. {p['title']}")
        
    choice = input("Select a number to delete: ")
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(prompts):
            p = prompts[idx]
            print(f"\nDetails for deletion:")
            print(f"Title: {p['title']}\nPrompt: {p['prompt']}\nCategory: {p['category']}\nTags: {','.join(p['tags'])}\nFavorite: {p['favorite']}")
            
            confirm = input(f"\nAre you sure you want to delete this prompt? (y/n): ")
            if confirm.lower() == 'y':
                prompts.pop(idx)
                save_to_csv(prompts)
                print("Deleted successfully.")
        else:
            print("Invalid selection.")
    except ValueError:
        print("Invalid input.")