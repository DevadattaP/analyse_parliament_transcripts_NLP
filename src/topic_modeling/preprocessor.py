import os

MINISTRY_DIR = "data/ministry_profiles"

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

if __name__ == "__main__":

    ministries = load_ministry_texts(MINISTRY_DIR)

    # write txt file (topic_modeling_input.txt) in format: id \t ministry_name \t text
    with open("data/topic_modeling/topic_modeling_input.txt", "w", encoding="utf-8") as f:
        for i, (name, text) in enumerate(ministries.items()):
            f.write(f"{i}\t{name}\t{text.replace('\n', ' ').replace('  ', ' ')}\n")
