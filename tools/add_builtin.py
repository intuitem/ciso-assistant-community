import re, os

# This is a temporary tool that adds "builtin: true" to all libraries stored as yaml files under ./backend/library/libraries.

current_path = "/".join(__file__.split("/")[:-1])
library_path = os.path.join(current_path, "..", "backend", "library", "libraries")
fnames = [fname for fname in os.listdir(library_path) if fname.endswith(".yaml")]

for fname in fnames:
    lib = os.path.join(library_path, fname)

    with open(lib, "r", encoding="utf-8") as f:
        content = f.read()
    lines = content.split("\n")

    if not any(re.match(r"^builtin.*:.*true", line) is not None for line in lines):
        lines.insert(1, "builtin: true")
        with open(lib, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"Library '{fname}' updated.")
