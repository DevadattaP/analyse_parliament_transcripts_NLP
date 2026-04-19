import os
import re
import json
import argparse
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS


# CONFIG
MINISTRY_DIR = "data/ministry_profiles"
MODEL_NAME = "all-MiniLM-L6-v2"
CACHE_DIR = "models"
STOPWORD_FILES = [
    "data/stopwords/GBparl_stopwords-empirical.txt",
    "data/stopwords/stopwords.txt",
]

MODE_OUTPUTS = {
    "1": "data/embeddings/ministry_embeddings.json",
    "2": "data/embeddings/ministry_embeddings1.json",
    "3": "data/embeddings/ministry_embeddings2.json",
    "4": "data/embeddings/ministry_embeddings3.json",
}

def load_ministry_embeddings(embed_file):
    with open(embed_file, "r") as f:
        data = json.load(f)

    # convert to numpy
    for k in data:
        data[k] = np.array(data[k])

    return data

# Load ministry texts
def load_ministry_texts(directory):
    ministries = {}
    for file in sorted(os.listdir(directory)):
        if file.endswith(".txt"):
            path = os.path.join(directory, file)
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            name = file.replace(".txt", "")
            ministries[name] = text
    return ministries


def load_stopwords(custom_files):
    stopwords = set(ENGLISH_STOP_WORDS)
    for custom_file in custom_files:
        if not os.path.exists(custom_file):
            print(f"Warning: stopword file not found: {custom_file}")
            continue
        with open(custom_file, "r", encoding="utf-8") as f:
            for line in f:
                word = line.strip().lower()
                if word:
                    stopwords.add(word)
    return stopwords


# Cleaning variants
def clean_text_basic(text):
    # remove bullet characters
    text = text.replace("\uf0b7", " ")

    # remove numbering like "1." "2."
    text = re.sub(r"\n?\d+\.\s*", " ", text)

    # replace newlines with space
    text = text.replace("\n", " ")

    # remove multiple spaces
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_text_advanced(text, stopwords=None):
    text = text.replace("\uf0b7", " ")
    text = re.sub(r"\n?\d+\.\s*", " ", text)
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    # remove all punctuation
    text = re.sub(r"[^\w\s]", "", text)
    
    # keep only alphabets, remove numbers
    text = re.sub(r"[^a-zA-Z\s]", "", text)

    # remove numbers
    text = re.sub(r"\d+", " ", text)

    # make everything lowercase
    text = text.lower()

    # tokenize
    words = text.split()

    if stopwords:
        words = [w for w in words if w not in stopwords and len(w) > 2]

    # remove duplicates while preserving order
    seen = set()
    unique_words = []
    for w in words:
        if w not in seen:
            seen.add(w)
            unique_words.append(w)

    return " ".join(unique_words)


# Build embeddings
def build_ministry_embeddings(ministries, mode):
    model = SentenceTransformer(MODEL_NAME, cache_folder=CACHE_DIR)
    use_stopwords = mode in {"2", "3", "4"}
    stopwords = load_stopwords(STOPWORD_FILES) if use_stopwords else None

    ministry_vectors = {}

    for name, text in ministries.items():
        if mode == "1":
            # full text, basic cleaning
            cleaned = clean_text_basic(text)
            embedding = model.encode(cleaned)
            ministry_vectors[name] = embedding.tolist()

        elif mode == "2":
            # full text, advanced cleaning + stopwords + dedupe
            cleaned = clean_text_advanced(text, stopwords)
            embedding = model.encode(cleaned)
            ministry_vectors[name] = embedding.tolist()

        elif mode in {"3", "4"}:
            # paragraph-level, advanced cleaning + stopwords + dedupe
            paragraphs = text.split("\n")
            cleaned_paragraphs = []
            for p in paragraphs:
                cleaned = clean_text_advanced(p, stopwords)
                if len(cleaned) > 10:
                    cleaned_paragraphs.append(cleaned)

            if not cleaned_paragraphs:
                fallback = clean_text_advanced(text, stopwords)
                cleaned_paragraphs = [fallback] if fallback else [""]

            embeddings = model.encode(cleaned_paragraphs, convert_to_numpy=True)

            if mode == "3":
                # store average paragraph embedding per ministry
                avg_embedding = np.mean(embeddings, axis=0)
                ministry_vectors[name] = avg_embedding.tolist()
            else:
                # mode == "4": store all paragraph embeddings
                ministry_vectors[name] = embeddings.tolist()

    return ministry_vectors


# Save embeddings
def save_embeddings(vectors, output_file):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(vectors, f)
    print("Embeddings saved to:", output_file)


def choose_mode_interactive():
    print("\nSelect embedding pipeline:")
    print("1) Basic clean + full-text embedding")
    print("2) Advanced clean + stopwords + dedupe + full-text embedding")
    print("3) Advanced clean + stopwords + dedupe + paragraph embeddings averaged")
    print("4) Advanced clean + stopwords + dedupe + save all paragraph embeddings")
    while True:
        choice = input("Enter choice [1-4]: ").strip()
        if choice in {"1", "2", "3", "4"}:
            return choice
        print("Invalid choice. Please enter 1, 2, 3, or 4.")


# MAIN
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build ministry embeddings with selectable preprocessing mode.")
    parser.add_argument("--mode", choices=["1", "2", "3", "4"], help="Pipeline mode. If not provided, menu is shown.")
    parser.add_argument("--output", help="Optional output JSON path. Overrides default for selected mode.")
    parser.add_argument("--ministry-dir", default=MINISTRY_DIR, help="Directory containing ministry .txt files.")
    args = parser.parse_args()

    selected_mode = args.mode or choose_mode_interactive()
    output_file = args.output or MODE_OUTPUTS[selected_mode]

    ministries = load_ministry_texts(args.ministry_dir)
    print("Loaded ministries:", len(ministries))
    print("Selected mode:", selected_mode)

    ministry_vectors = build_ministry_embeddings(ministries, selected_mode)
    save_embeddings(ministry_vectors, output_file)
