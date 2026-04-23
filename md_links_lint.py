import os
import re
from collections import defaultdict

# Regex pattern to match </some/path/file.md>
LINK_PATTERN = re.compile(r"</([\S ][^>\n]*?\.md)>")

def find_all_files(root_dir):
    all_files = set()
    for dirpath, _, filenames in os.walk(root_dir):
        for fname in filenames:
            rel_path = os.path.relpath(os.path.join(dirpath, fname), root_dir)
            all_files.add(rel_path.replace("\\", "/"))  # Normalize path separators
    return all_files

def find_links_in_file(file_path):
    links = set()
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        for match in LINK_PATTERN.finditer(content):
            links.add(match.group(1))
    return links

def main():
    root_dir = os.getcwd()
    all_files = find_all_files(root_dir)

    # Only consider markdown files for searching links
    markdown_files = [f for f in all_files if f.endswith(".md")]

    referenced_files = set()
    bad_links = defaultdict(list)  # link_path -> [files it's mentioned in]

    for md_file in markdown_files:
        abs_path = os.path.join(root_dir, md_file)
        links = find_links_in_file(abs_path)
        for link in links:
            if link in all_files:
                referenced_files.add(link)
            else:
                bad_links[link].append(md_file)

    # Unreferenced files
    unreferenced_files = [
        f for f in markdown_files if f not in referenced_files
    ]

    # Report
    if bad_links:
        print("❌ Bad Links (do not point to any file in repo):")
        for link, sources in bad_links.items():
            print(f"  - {link} (linked in: {', '.join(sources)})")
    else:
        print("✅ No bad links found.")

    if unreferenced_files:
        print("\n📂 Unreferenced Markdown Files:")
        for f in unreferenced_files:
            print(f"  - {f}")
    else:
        print("\n✅ All markdown files are referenced.")

if __name__ == "__main__":
    main()
