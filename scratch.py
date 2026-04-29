import re

with open("AGV_Webots_World_and_Controllers/worlds/AGV_Warehouse_World.wbt", "r") as f:
    content = f.read()

# Pattern to find Solid nodes with name "Work_Island_X"
pattern = re.compile(r'Solid\s*\{\s*translation\s+([-\d\.]+)\s+([-\d\.]+)\s+([-\d\.]+).*?size\s+([-\d\.]+)\s+([-\d\.]+)\s+([-\d\.]+).*?name\s+"Work_Island_[^"]+"', re.DOTALL)
matches = pattern.findall(content)
for m in matches:
    print(f"x: {m[0]}, y: {m[1]}, w: {m[3]}, h: {m[4]}")
