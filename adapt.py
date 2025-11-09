import re

def replace_commas_in_quotes(text, replacement=";"):
    # This replaces ALL commas that appear between a pair of quotes
    return re.sub(r'"(.*?)"',
                  lambda m: '"' + m.group(1).replace(',', replacement) + '"',
                  text)

input_file = "all.csv"
output_file = "all_patched.csv"

# Regex to match the JLPT keyword pattern
jlpt_pattern = re.compile(r"JLPT_N?\d+")

with open(input_file, "r", encoding="utf-8") as fin, open(output_file, "w", encoding="utf-8") as fout:
    for line in fin:
        # Skip empty lines
        if not line.strip():
            continue

        line_new = replace_commas_in_quotes(line)

        parts = line_new.strip().split(",")
        if len(parts) < 3:
            continue  # Skip malformed lines

        if parts[0] == "expression":
            fout.write("expression,reading,meaning,tags\n")
            continue

        # Extract JLPT_* from the 4th column (index 3) or beyond
        match = jlpt_pattern.search(line_new)
        jlpt_level = match.group(0) if match else ""

        # Reconstruct line with only JLPT_* in column 3
        cleaned_line = ",".join(parts[:3]) + ("," + jlpt_level if jlpt_level else "")
        fout.write(cleaned_line + "\n")

print("Done. Cleaned lines written to", output_file)
