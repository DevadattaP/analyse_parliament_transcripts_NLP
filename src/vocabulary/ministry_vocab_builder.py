import os
import re
import json
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer


# -----------------------------------
# CONFIG
# -----------------------------------
MINISTRY_DIR = "data/ministry_profiles"
STOPWORDS_FILE = "data/stopwords/GBparl_stopwords-empirical.txt"
OUTPUT_FILE = "data/vocabulary/ministry_tfidf_vocab.json"
TOP_N = 100
MAX_MINISTRY_REPEAT = 10


# -----------------------------------
# Load Custom Stopwords
# -----------------------------------
def load_custom_stopwords(stopword_file):
    with open(stopword_file, "r", encoding="utf-8") as f:
        stopwords = [line.strip().lower() for line in f if line.strip()]
    return stopwords

# -----------------------------------
# 1. Text Cleaning Function
# -----------------------------------
def clean_text(text_data, stopwords=None):
    """
    - Lowercase
    - Remove numbers
    - Keep only alphabets
    - Remove extra spaces
    """

    text_data = text_data.lower()

    # Remove numbers
    text_data = re.sub(r'\d+', ' ', text_data)

    # Keep only alphabets
    text_data = re.sub(r'[^a-z\s]', ' ', text_data)

    # Remove extra spaces
    text_data = re.sub(r'\s+', ' ', text_data).strip()
    
    # Remove stopwords
    if stopwords:
        words = [w for w in text_data.split() if w not in stopwords]
        text_data = " ".join(words)

    return text_data


# -----------------------------------
# 2. Load Ministry Text Files
# -----------------------------------
def load_ministry_files(directory, stopwords=None):
    ministries = {}

    for file in os.listdir(directory):
        if file.endswith(".txt"):
            file_path = os.path.join(directory, file)

            with open(file_path, "r", encoding="utf-8") as f:
                text_data = f.read()

            cleaned = clean_text(text_data, stopwords)

            ministry_name = file.replace(".txt", "")
            ministries[ministry_name] = cleaned

    return ministries


# -----------------------------------
# 3. TF-IDF Keyword Extraction
# -----------------------------------
def extract_tfidf_keywords(ministries, top_n=100, max_ministry_occurrence=10):
    docs = list(ministries.values())
    names = list(ministries.keys())
    
    vectorizer = TfidfVectorizer(
        stop_words='english',
        max_df=0.85,
        min_df=3,
        ngram_range=(1, 2),  # unigrams + bigrams
        token_pattern=r'\b[a-z]{3,}\b'  # only alphabet words >=3 letters
    )

    tfidf_matrix = vectorizer.fit_transform(docs)
    feature_names = vectorizer.get_feature_names_out()

    # -----------------------------------
    # Count in how many ministries each word appears
    # -----------------------------------
    from collections import defaultdict
    word_ministry_count = defaultdict(int)

    for col_idx, word in enumerate(feature_names):
        column = tfidf_matrix[:, col_idx].toarray().flatten()
        count = (column > 0).sum()
        word_ministry_count[word] = count

    # -----------------------------------
    # Extract filtered top words per ministry
    # -----------------------------------
    ministry_keywords = {}

    for idx, name in enumerate(names):
        row = tfidf_matrix[idx].toarray().flatten()

        # Get sorted indices by tfidf score
        sorted_indices = row.argsort()[::-1]

        keywords = []
        for i in sorted_indices:
            word = feature_names[i]

            # Skip words appearing in too many ministries
            if word_ministry_count[word] > max_ministry_occurrence:
                continue

            if row[i] > 0:
                keywords.append(word)

            if len(keywords) >= top_n:
                break

        ministry_keywords[name] = keywords

    return ministry_keywords


# -----------------------------------
# 4. Save Vocabulary File
# -----------------------------------
def save_vocab(vocab_dict, output_file):
    Path(os.path.dirname(output_file)).mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(vocab_dict, f, indent=4)

    print(f"Vocabulary saved to: {output_file}")


if __name__ == "__main__":

    print("Loading stopwords...")
    custom_stopwords = load_custom_stopwords(STOPWORDS_FILE)
    
    print("Loading ministry files...")
    ministries = load_ministry_files(MINISTRY_DIR, custom_stopwords)
    print(f"Total ministries loaded: {len(ministries)}")

    print("Extracting TF-IDF keywords...")
    ministry_keywords = extract_tfidf_keywords(ministries, top_n=TOP_N, max_ministry_occurrence=MAX_MINISTRY_REPEAT)

    print("Saving vocabulary...")
    save_vocab(ministry_keywords, OUTPUT_FILE)

    print("Done.")
