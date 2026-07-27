print("__name__ in text_tools.py ->", __name__)

def count_vowels(s):
    s = s.lower()
    vowels = "aeiou"
    count = 0
    for ch in s:
        if ch in vowels:
            count += 1
    return count

if __name__ == "__main__":
    sample = "Hello, World!"
    print("Demo: count_vowels(", sample, ") ->", count_vowels(sample))