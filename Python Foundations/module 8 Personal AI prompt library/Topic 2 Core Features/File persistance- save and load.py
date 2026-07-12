def save_prompts(Prompts, filename):
    with open(filename, "w") as f:
        for prompt in Prompts:
            tags_str = ",".join(prompt["tags"]) 
            line = f"{prompt['title']}|{prompt['category']}|{prompt['prompt']}|{tags_str}|{prompt['favorite']}"
            f.write(line + "\n")
def load_prompts(filename):
    prompts = []
    try:
        with open(filename, "r") as f:
            for line in f:
                line = line.strip()
                parts = line.split("|")
                raw_tags = parts[3].split(",")
                clean_tags = []
                for tags in raw_tags:
                    trimmed_tags = tags.strip()
                    if trimmed_tags:
                        clean_tags.append(trimmed_tags)
                fav_text = parts[4].strip().lower()
                is_favorite = fav_text in ["true", "1", "yes"]
                prompt = {
                    "title": parts[0],
                    "category": parts[1],
                    "prompt": parts[2],
                    "tags": clean_tags,
                    "favorite": is_favorite
                }
                prompts.append(prompt)
    except FileNotFoundError:
        return []   
    return prompts         