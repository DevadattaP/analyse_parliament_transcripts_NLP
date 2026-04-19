import os
import json
import argparse
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from src.embedding.topic_embeddings import load_topic_embeddings
from src.embedding.ministry_embeddings import load_ministry_embeddings
import warnings
warnings.filterwarnings("ignore")


MINISTRY_EMBED_FILES = {
    "1": "data/embeddings/ministry_embeddings.json",
    "2": "data/embeddings/ministry_embeddings1.json",
    "3": "data/embeddings/ministry_embeddings2.json",
    "4": "data/embeddings/ministry_embeddings3.json",
}

MAPPING_OUTPUTS = {
    ("1", "single"): "data/topic_modeling/topic_ministry_mapping.csv",
    ("2", "single"): "data/topic_modeling/topic_ministry_mapping1.csv",
    ("3", "single"): "data/topic_modeling/topic_ministry_mapping2.csv",
    ("4", "mean"): "data/topic_modeling/topic_ministry_mapping3_mean.csv",
    ("4", "max"): "data/topic_modeling/topic_ministry_mapping3_max.csv",
    ("4", "topk_mean"): "data/topic_modeling/topic_ministry_mapping3_topk.csv",
}

def save_state_based_topic_ministry_tables():
    # load doc-word-topic matrix
    state = pd.read_csv("data/topic_modeling/state.csv")
    counts = state.groupby(["DocID", "Topic"]).size().unstack(fill_value=0)
    # proportion of words assigned to each topic for each document
    proportions = counts.div(counts.sum(axis=1), axis=0)
    # proportion of words assigned to each document for each topic
    proportions_T = counts.T.div(counts.T.sum(axis=1), axis=0) 
    
    state["DominantTopic"] = state.groupby("DocID")["Topic"].transform(lambda x: x.value_counts().idxmax())
    dominant_topics = state[["DocID", "DominantTopic"]].drop_duplicates()
    
    topic_docs = state.groupby("Topic")["DocID"].apply(lambda x: x.value_counts().idxmax()).reset_index()

    # read ministry names from data/ministry_profiles (<ministry_name>.txt file for each ministry)
    ministry_names = []
    for filename in os.listdir("data/ministry_profiles"):
        if filename.endswith(".txt"):
            ministry_names.append(filename[:-4])  # remove .txt extension
            
    #replace topdocid in topic_docs with ministry name if it matches. then plot the distribution of ministries for each topic.
    for i, row in topic_docs.iterrows():
        topic_docs.at[i, "DocID"] = ministry_names[row["DocID"]]
    
    # rename columns to Topic and Ministries
    topic_docs.columns = ["Topic", "Ministry"]
    # print(topic_docs)
    
    # top ministry in each topic, save csv
    topic_docs.to_csv("data/topic_modeling/top_ministry_per_topic.csv", index=False)
    
    # dominant_topics has DocID and DominantTopic
    # i want to list for each topic, the documents have been assigned
    topic_documents = dominant_topics.groupby("DominantTopic")["DocID"].apply(list).reset_index()
    
    # replace docids list in topic_documents with ministry_name 
    for i, row in topic_documents.iterrows():
        topic_documents.at[i, "DocID"] = [ministry_names[doc_id] for doc_id in row["DocID"]]
    
    # rename columns to Topic and Ministries
    topic_documents.columns = ["Topic", "Ministries"]
    # print(topic_documents)
    
    # top topics for each ministry, save csv
    topic_documents.to_csv("data/topic_modeling/top_topics_per_ministry.csv", index=False)


def compute_score(topic_vec, ministry_vec, mode, aggregation="single", topk=5):
    topic_vec = np.array(topic_vec).reshape(1, -1)
    ministry_vec = np.array(ministry_vec)

    if mode in {"1", "2", "3"}:
        return cosine_similarity(topic_vec, ministry_vec.reshape(1, -1))[0][0]

    # mode 4: ministry has paragraph embeddings (n_paragraphs, dim)
    if ministry_vec.ndim == 1:
        ministry_vec = ministry_vec.reshape(1, -1)

    scores = cosine_similarity(topic_vec, ministry_vec)[0]

    if aggregation == "max":
        return float(np.max(scores))
    if aggregation == "topk_mean":
        k = min(topk, len(scores))
        top_scores = np.sort(scores)[-k:]
        return float(np.mean(top_scores))
    return float(np.mean(scores))  # default mean


def build_topic_ministry_mapping(topic_embeddings, ministry_embeddings, mode, aggregation="single", topk=5):
    topics = list(topic_embeddings.keys())
    ministries = list(ministry_embeddings.keys())

    sim_matrix = {}
    for t in topics:
        sim_matrix[t] = {}
        for m in ministries:
            sim_matrix[t][m] = compute_score(
                topic_embeddings[t],
                ministry_embeddings[m],
                mode=mode,
                aggregation=aggregation,
                topk=topk,
            )

    sim_matrix_df = pd.DataFrame(sim_matrix)
    max_sim_score = sim_matrix_df.max(axis=1)
    sim_matrix_df["Most Similar Topic"] = sim_matrix_df.idxmax(axis=1)

    topic_ministry_df = pd.DataFrame(
        {"TopicID": sim_matrix_df["Most Similar Topic"], "Score": max_sim_score}
    ).reset_index().rename(columns={"index": "Ministry"})

    return sim_matrix_df, topic_ministry_df[["TopicID", "Ministry", "Score"]]


def choose_mode_interactive():
    print("\nSelect ministry embedding source:")
    print("1) ministry_embeddings.json")
    print("2) ministry_embeddings1.json")
    print("3) ministry_embeddings2.json")
    print("4) ministry_embeddings3.json (paragraph-level)")
    while True:
        choice = input("Enter choice [1-4]: ").strip()
        if choice in {"1", "2", "3", "4"}:
            return choice
        print("Invalid choice. Please enter 1, 2, 3, or 4.")


def choose_aggregation_interactive():
    print("\nMode 4 aggregation:")
    print("1) mean")
    print("2) max")
    print("3) topk_mean (default k=5)")
    while True:
        choice = input("Enter choice [1-3]: ").strip()
        if choice == "1":
            return "mean"
        if choice == "2":
            return "max"
        if choice == "3":
            return "topk_mean"
        print("Invalid choice. Please enter 1, 2, or 3.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Topic-ministry mapping across ministry embedding variants.")
    parser.add_argument("--mode", choices=["1", "2", "3", "4"], help="Ministry embedding mode")
    parser.add_argument("--topic-embeddings", default="data/embeddings/topic_embeddings.json")
    parser.add_argument("--ministry-embeddings", help="Override ministry embedding file path")
    parser.add_argument("--aggregation", choices=["single", "mean", "max", "topk_mean"], default=None)
    parser.add_argument("--topk", type=int, default=5)
    parser.add_argument("--output", help="Override output CSV path")
    parser.add_argument("--skip-state-tables", action="store_true")
    args = parser.parse_args()

    selected_mode = args.mode or choose_mode_interactive()
    ministry_embed_file = args.ministry_embeddings or MINISTRY_EMBED_FILES[selected_mode]

    if selected_mode == "4":
        aggregation = args.aggregation or choose_aggregation_interactive()
        if aggregation == "single":
            aggregation = "mean"
    else:
        aggregation = "single"

    default_output = MAPPING_OUTPUTS.get((selected_mode, aggregation), "data/topic_modeling/topic_ministry_mapping.csv")
    output_file = args.output or default_output
    # if choosen is topk_mean, then replace topk in ouptut filename with actual k value
    if aggregation == "topk_mean":
        output_file = output_file.replace("topk", f"top{args.topk}")
    
    if not args.skip_state_tables:
        save_state_based_topic_ministry_tables()

    topic_embeddings = load_topic_embeddings(args.topic_embeddings)
    ministry_embeddings = load_ministry_embeddings(ministry_embed_file)

    _, mapping_df = build_topic_ministry_mapping(
        topic_embeddings=topic_embeddings,
        ministry_embeddings=ministry_embeddings,
        mode=selected_mode,
        aggregation=aggregation,
        topk=args.topk,
    )

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    mapping_df.to_csv(output_file, index=False)
    print(f"Saved: {output_file}")
