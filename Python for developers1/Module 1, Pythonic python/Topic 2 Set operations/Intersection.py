frontend = {"HTML", "CSS", "JavaScript"}
backend = {"Python", "Databases", "JavaScript"}

shared1 = frontend & backend
print(shared1)

shared2 = frontend.intersection(backend)
print(shared2)

title1 = {"Closer", "sorry", "loose"}
title2 = {"stiches", "grenade", "sorry"}
shared = title1.intersection(title2)
print(shared)
