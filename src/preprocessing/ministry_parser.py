import re
import os
from pathlib import Path
import pdfplumber



PDF_PATH = "data/references/Ministries.pdf"
OUTPUT_DIR = "data/ministry_profiles"


# -----------------------------------
# 1. Extract Full PDF Text
# -----------------------------------
def extract_full_text(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

# -----------------------------------
# 2. Split Ministries Using
#    Ministry of ... \n Full Form:
# -----------------------------------
def split_ministries(text):
    """
    Splits based on:
    Ministry of <Name>
    Full Form: ...
    """

    pattern = r"(Ministry of .*?)\nFull Form:"
    
    matches = list(re.finditer(pattern, text))

    ministries = {}

    for i, match in enumerate(matches):
        ministry_name = match.group(1).strip()

        start = match.start(1)
        end = matches[i+1].start(1) if i+1 < len(matches) else len(text)

        ministry_text = text[start:end].strip()
        
        # CLEAN TEXT HERE
        full_text = clean_pdf_text(ministry_text)
        
        ministries[ministry_name] = full_text

    return ministries


# -----------------------------------
# 3. Clean Each Ministry's Text
# -----------------------------------
def clean_pdf_text(text):
    """
    Fix line breaks, bullets, spacing issues from PDF extraction
    """

    # Remove weird bullet characters
    text = re.sub(r"[\uf000-\uf0ff]", "", text)
    
    # Remove numbered list patterns (e.g., "1. ", "2. ", etc.)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    
    # remove all special characters like (), [, ], {, }, ;, :, &
    text = re.sub(r"[()\[\]{};:&,]", "", text)

    # Remove multiple spaces
    text = re.sub(r"[ \t]+", " ", text)

    # Fix broken lines inside sentences
    # Join lines where next line starts with lowercase
    text = re.sub(r"\n([a-z])", r" ", text)

    # Join lines ending without punctuation
    text = re.sub(r"(?<![.\n])\n(?!\n)", " ", text)

    # Remove extra newlines
    text = re.sub(r"\n\s*\n", "\n\n", text)

    return text.strip()


# -----------------------------------
# 4. Save Each Ministry
# -----------------------------------
def save_ministries(ministries, output_dir):
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    for name, content in ministries.items():
        safe_name = re.sub(r"[^\w]+", "_", name)

        file_path = os.path.join(output_dir, f"{safe_name}.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)


if __name__ == "__main__":
    full_text = extract_full_text(PDF_PATH)

    ministries = split_ministries(full_text)

    print(f"Total Ministries Found: {len(ministries)}")

    save_ministries(ministries, OUTPUT_DIR)
