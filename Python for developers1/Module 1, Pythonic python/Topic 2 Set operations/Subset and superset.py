prereqs = {"Math 101", "Intro to CS"}
student_courses = {"Intro to CS", "Math 101", "English 101"}

print(prereqs.issubset(student_courses))
print(student_courses.issuperset(prereqs))

core_games = {"Bowling", "Skiing", "Ziplining"}
branch_B = {"Tramboline", "Bowling", "Skiing", "Ziplining"}
print(core_games.issubset(branch_B))
print(branch_B.issuperset(core_games))