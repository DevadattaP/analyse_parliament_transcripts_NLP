import re
import pdfplumber
from pathlib import Path


PDF_FILES = [
    "data/references/1614011758631.12_important_partliament_term.pdf",
    "data/references/IMPORTANTPARLIAMENTARY_TERMS_EH_b93dbc8c40.pdf"
]

OUTPUT_FILE = "data/vocabulary/parliament_vocab.txt"


def extract_text_from_pdf(pdf_path):
    full_text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text.append(text)
    return "\n".join(full_text)


def extract_terms(text):
    terms = set()

    lines = text.split("\n")

    for line in lines:
        line = line.strip()

        # ---- Pattern 1: Numbered format like (1) "Act"-- ----
        match1 = re.match(r'^\(\d+\)\s*[\"“]?(.+?)[\"”]?\s*[-–]', line)
        if match1:
            term = match1.group(1).strip()
            terms.add(clean_term(term))
            continue

        # ---- Pattern 2: Standalone heading word like Act (of Parliament) ----
        match2 = re.match(r'^[A-Z][A-Za-z\s\-\(\)\/]+$', line)
        if match2 and len(line.split()) <= 6:
            terms.add(clean_term(line))
            continue

    return terms


def clean_term(term):
    term = term.strip()
    term = re.sub(r'\s+', ' ', term)        # remove extra spaces
    term = term.replace("  ", " ")
    return term


def build_vocab():
    all_terms = set()

    for pdf_path in PDF_FILES:
        print(f"Processing: {pdf_path}")
        text = extract_text_from_pdf(pdf_path)
        terms = extract_terms(text)
        all_terms.update(terms)

    # Sort alphabetically
    sorted_terms = sorted(all_terms)

    # Create directory if not exists
    Path("data/vocabulary").mkdir(parents=True, exist_ok=True)

    # Save to file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for term in sorted_terms:
            f.write(term + "\n")

    print(f"\nVocabulary saved to {OUTPUT_FILE}")
    print(f"Total unique terms extracted: {len(sorted_terms)}")

if __name__ == "__main__":
    build_vocab()
