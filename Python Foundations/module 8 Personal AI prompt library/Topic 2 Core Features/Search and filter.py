def search_prompts(prompts):
    user_input = input("Enter the keyword: ")
    search_term = user_input.strip().lower()
    results = []

    for prompt in prompts:
        title_match = search_term in prompt["title"].lower()
        text_match = search_term in prompt["prompt"].lower()
        tag_match = False
        for tag in prompt["tags"]:
            if search_term in tag.lower():
                tag_match = True
                break
        
        match_found = False
        if title_match:
            match_found = True
        elif text_match:
            match_found = True
        elif tag_match:
            match_found = True

        if match_found:
            results.append(prompt)

    if len(results) > 0:
        print(f"\nFound {len(results)} matching prompt(s):")
        for item in results:
            print(f"- {item['title']}")
    else:
        print("\nNo prompts were found matching that keyword.")
        
    return results

def filter_by_category(prompts):
    unique_categories = []
    for prompt in prompts:
        current_cat = prompt["category"]
        
        already_exists = False
        for category in unique_categories:
            if category == current_cat:
                already_exists = True
                break
        
        if already_exists == False:
            unique_categories.append(current_cat)
            
    print("Available categories:")
    for index, category in enumerate(unique_categories, start=1):
        print(f"{index}. {category}")
        
    choice = input("Enter the number of the category to filter by: ")
    
    try:
        idx = int(choice) - 1
    except ValueError:
        print("Invalid selection.")
        return []
    
    filtered_results = []
    if idx >= 0 and idx < len(unique_categories):
        selected_category = unique_categories[idx]
        
        for prompt in prompts:
            if prompt["category"].lower() == selected_category.lower():
                filtered_results.append(prompt)
        
        if len(filtered_results) > 0:
            print(f"\nFound {len(filtered_results)} prompt(s) in '{selected_category}':")
            for item in filtered_results:
                print(f"- {item['title']}")
        else:
            print(f"\nNo prompts were found for the category: {selected_category}")
    else:
        print("Invalid selection.")
        
    return filtered_results