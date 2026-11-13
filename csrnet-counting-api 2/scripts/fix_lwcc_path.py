from pathlib import Path

import lwcc.util.functions as lwcc_functions

functions_file = Path(lwcc_functions.__file__)
content = functions_file.read_text(encoding="utf-8")

replacements = {
    'Path("/.lwcc/weights").mkdir(parents=True, exist_ok=True)': (
        '(Path.home() / ".lwcc" / "weights").mkdir('
        'parents=True, exist_ok=True)'
    ),
    'output = os.path.join(home, "/.lwcc/weights/", file_name)': (
        'output = os.path.join(home, ".lwcc", "weights", file_name)'
    ),
}

changed = False
for old_code, new_code in replacements.items():
    if old_code in content:
        content = content.replace(old_code, new_code)
        changed = True

if changed:
    functions_file.write_text(content, encoding="utf-8")
    print("LWCC weights paths fixed successfully.")
else:
    print("No incorrect LWCC paths were found; they may already be fixed.")

print(f"Checked file: {functions_file}")
