import yaml, json, re

def resources(args):
    return [{"url": "foo", "type": "module"}, {"url": "booboo"}]

def parse_line(line):
    match = re.match(r"^(.*)@@(.+)@@(.*)", line)
    if match:
        evaled = eval(match.group(2))
        if type(evaled) is str:
            prefix_str = "\n" + " " * len(match.group(1))
            re.sub(r"^", match.group(1), line)
            re.sub(r"\n", prefix_str, line)
        else:
            evaled = evaled.__repr__()
            line = f"{match.group(1)}{evaled}{match.group(3)}"
    return line

with open('file.yaml') as f:
    lines = [parse_line(line) for line in f]

print("".join(lines))
data = yaml.safe_load("".join(lines))
print(yaml.dump(data))
