import cutlet
katsu = cutlet.Cutlet()

input_file = "all_patched.csv"
output_file = "all_hiragana.csv"

with open(input_file, "r", encoding="utf-8") as fin, open(output_file, "w", encoding="utf-8") as fout:
    for line in fin:
        # Skip empty lines
        if not line.strip():
            continue

        parts = line.strip().split(",")
        if len(parts) < 4:
            continue  # Skip malformed lines

        if parts[0] == "expression":
            fout.write(parts[0] + "," + parts[1] + ",romaji," + parts[2] + "," + parts[3] + "\n")
            continue

        romaji = katsu.romaji(parts[1]).lower().replace(" ", "")
        fout.write(parts[0] + "," + parts[1] + "," + romaji + "," + parts[2] + "," + parts[3] + "\n")

print("Done. Cleaned lines written to", output_file)


katsu.romaji("カツカレーは美味しい")