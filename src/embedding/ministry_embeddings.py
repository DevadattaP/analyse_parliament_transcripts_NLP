import os
import re
import json
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS


# --------------------------------
# CONFIG
# --------------------------------
MINISTRY_DIR = "data/ministry_profiles"
OUTPUT_FILE = "data/embeddings/ministry_embeddings1.json"
STOPWORD_FILE = "../data/stopwords/GBparl_stopwords-empirical.txt"
MODEL_NAME = "all-MiniLM-L6-v2"
CACHE_DIR = "models"

def load_stopwords(custom_file):

    stopwords = set(ENGLISH_STOP_WORDS)

    # load domain stopwords
    with open(custom_file, "r", encoding="utf-8") as f:
        for line in f:
            word = line.strip().lower()
            if word:
                stopwords.add(word)

    return stopwords


# --------------------------------
# Load ministry texts
# --------------------------------
def load_ministry_texts(directory):

    ministries = {}

    for file in os.listdir(directory):
        if file.endswith(".txt"):

            path = os.path.join(directory, file)

            with open(path, "r", encoding="utf-8") as f:
                text = f.read()

            name = file.replace(".txt", "")
            ministries[name] = text

    return ministries


def clean_text(text, stopwords=None):

    # remove bullet characters
    text = text.replace("\uf0b7", " ")

    # remove numbering like "1." "2."
    text = re.sub(r"\n?\d+\.\s*", " ", text)

    # replace newlines with space
    text = text.replace("\n", " ")

    # remove multiple spaces
    text = re.sub(r"\s+", " ", text)
    
    # remove all punctuation
    text = re.sub(r'[^\w\s]', '', text)
    
    # keep only alphabets, remove numbers
    text = re.sub(r'[^a-zA-Z\s]', '', text)

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


# --------------------------------
# Build embeddings
# --------------------------------
def build_ministry_embeddings(ministries):

    model = SentenceTransformer(MODEL_NAME, cache_folder=CACHE_DIR)

    stopwords = load_stopwords(STOPWORD_FILE)
    
    ministry_vectors = {}

    for name, text in ministries.items():

        cleaned = clean_text(text, stopwords)

        embedding = model.encode(cleaned)

        ministry_vectors[name] = embedding.tolist()

    return ministry_vectors


# --------------------------------
# Save embeddings
# --------------------------------
def save_embeddings(vectors, output_file):

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(vectors, f)

    print("Embeddings saved to:", output_file)


# --------------------------------
# MAIN
# --------------------------------
if __name__ == "__main__":

    ministries = load_ministry_texts(MINISTRY_DIR)

    print("Loaded ministries:", len(ministries))

    ministry_vectors = build_ministry_embeddings(ministries)

    save_embeddings(ministry_vectors, OUTPUT_FILE)
