import json

# Python dictionary 
career_profile = {
    "credentials": {"user_email": "branicenafula6@gmail.com", "password": "1668bw"},
    "professional_info": {"name": "Branice Nafula", "skills": ["Python", "SQL", "AI engineering"]}
}

# Saving the dictionary to a file
with open('career_profile.json', 'w') as f:
    json.dump(career_profile, f, indent=4)

# Load the JSON data back into a dictionary
with open('career_profile.json', 'r') as file:
    data = json.load(file)

# Add a new skill
data['professional_info']['skills'].append("frontend developer")

# Save the updated data back to the same file
with open('career_profile.json', 'w') as file:
    json.dump(data, file, indent=4)

print("New skill added and file updated.")