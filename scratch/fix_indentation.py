import re

def fix_indentation():
    with open("backend/scraper.py", "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Find where the for loop starts and ends
    start_idx = -1
    for i, line in enumerate(lines):
        if "url = site[\"url\"]" in line and "name = site[\"name\"]" in lines[i+1]:
            start_idx = i
            break
            
    end_idx = -1
    for i in range(start_idx, len(lines)):
        if "self.execution.valid_leads = contacts_added" in lines[i]:
            end_idx = i + 1 # include the commit on the next line
            break

    print(f"Indenting from line {start_idx} to {end_idx}")

    # Indent lines by 4 spaces
    for i in range(start_idx, end_idx + 1):
        # only indent if it's not an empty line
        if lines[i].strip():
            lines[i] = "    " + lines[i]

    # Now we need to add search_iteration += 1 after the for loop ends
    # The for loop ends after end_idx
    # Let's insert search_iteration += 1
    
    # Check if search_iteration += 1 is already there
    has_increment = False
    for i in range(end_idx, len(lines)):
        if "search_iteration += 1" in lines[i]:
            has_increment = True
            break
            
    if not has_increment:
        lines.insert(end_idx + 1, "            search_iteration += 1\n")

    with open("backend/scraper.py", "w", encoding="utf-8") as f:
        f.writelines(lines)

    print("Fixed indentation.")

fix_indentation()
