title = input("Title: ").strip()
author = input("Author: ").strip()
category = input("Category: ").strip()
word_count = int(input("Word count: ").strip())
clean_title = title
slug_base = clean_title.replace("!", "").replace("?", "").lower()
slug = "-".join(slug_base.split())
clean_author = author.title()
clean_category = category.upper()
formatted_words = f"{word_count:,}"
reading_minutes = word_count // 200
title_length = len(clean_title)

print(f"Title: {clean_title}")
print(f"Slug: {slug}")
print(f"Author: {clean_author}")
print(f"Category: {clean_category}")
print(f"Word count: {formatted_words}")
print(f"Reading time: {reading_minutes} min")
print(f"Title length: {title_length} chars")