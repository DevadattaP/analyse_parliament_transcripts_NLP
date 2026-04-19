import json
import numpy as np
import pandas as pd

def load_topic_embeddings(embedding_file):
    with open(embedding_file, "r") as f:
        data = json.load(f)
    return {k: np.array(v) for k, v in data.items()}

if __name__ == "__main__":

    topic_summary = pd.read_csv("data/topic_modeling/keys.csv")

    # Create topic text dictionary
    topic_texts = {}

    for _, row in topic_summary.iterrows():
        topic_id = row["Topic"]
        words = row["Words"]
        topic_texts[topic_id] = words

    # print topic texts in json format
    print(json.dumps(topic_texts, indent=4))

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2", cache_folder="models")

    topic_embeddings = {}
    for topic_id, text in topic_texts.items():
        topic_embeddings[topic_id] = model.encode(text)
        
    # save topic embeddings to json
    topic_embeddings_json = {k: v.tolist() for k, v in topic_embeddings.items()}
    with open("data/embeddings/topic_embeddings.json", "w") as f:
        json.dump(topic_embeddings_json, f)
