# 🇮🇳 Indian Parliamentary Proceedings – Ministry Classification & Analytics

## 📋 Project Description

This project analyzes Indian parliamentary proceedings using Natural Language Processing (NLP).
The main objective is to automatically identify which ministry or department is being discussed in each paragraph of a parliamentary transcript.

The system processes parliamentary session documents such as:

- Budget speeches
- Bill discussions
- Question–Answer sessions
- Ministerial statements
- General debates

It converts long unstructured PDF documents into structured data and generates ministry-wise statistics.

## 🎯 Core Objectives

- Extract clean text from parliamentary PDFs
- Identify speaker segments
- Perform Named Entity Recognition (NER)
- Classify each paragraph into a relevant ministry
- Generate ministry distribution across the document
- Produce speaker-wise and time-based ministry statistics
- Provide structured JSON outputs and visualizations

## 🧠 Main NLP Task

We model ministry detection as a paragraph-level multi-class classification problem.
Each paragraph is assigned to one ministry such as:

- Ministry of Finance
- Ministry of Textiles
- Ministry of Mines
- Ministry of Electronics and IT
- Ministry of Agriculture
- etc.

## ⚙️ System Architecture

The system follows a document-processing pipeline:

1. Preprocessing
    - Convert PDF to text
    - Remove headers, footers, formatting noise
    - Segment into speaker turns and paragraphs

2. Speaker Identification
    - Rule-based detection of speaker names and roles

3. Ministry Classification
    - Baseline: Keyword-based ministry scoring
    - Main Model: Embedding-based semantic similarity between paragraph and official ministry descriptions
    - Optional: Supervised classifier (if annotated data available)

4. Analytics
    - Ministry distribution across document
    - Speaker-wise ministry coverage
    - Time-based statistics
    - Structured JSON output
    - Visual charts

## Project Structure

```bash
parliament-nlp-analysis/
├── documentation/         # Reports and project documentation
├── data/
│   ├── ministry_profiles/ # Official ministry descriptions
│   ├── references/        # Reference documents for vocab, context, etc
│   ├── stopwords/         # stopwords txt files for cleaning
│   ├── topic_modeling/    # input and output files for topic modeling tool (online tool by David Mimno)
│   ├── vocabulary/        # Vocabulary for validating parliamentary terms
│   └── embeddings/        # embeddings json files for ministry classification
├── src/
│   ├── preprocessing/     # PDF parsing and cleaning
│   ├── embedding/         # Embedding generation for ministries, paragraphs and topics
│   ├── classification/    # Scripts for ministry classification
│   ├── topic_modeling/    # topic-ministry mapping and related utilities
│   ├── vocabulary/        # Building parliamentary vocabulary
│   └── api/               # FastAPI service
├── notebooks/             # Experiments and analysis
├── models/                # Saved transformer model
├── requirements.txt
├── config.yaml
├── .gitignore
└── README.md
```

## ⚙️ Installation & Setup

### Prerequisites

- Python 3.12+
- Git

### Step 1: Clone the Repository

```bash
git clone https://github.com/DevadattaP/analyse_parliament_transcripts_NLP.git
cd analyse_parliament_transcripts_NLP
```

### Step 2: Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate    # for Linux/Mac
venv\Scripts\activate       # for Windows
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

## 🚀 Quick Start

### Start Web API Server

```bash
uvicorn src.api.main:app --reload
```

The FastAPI server will start at <http://localhost:8000>

API documentation is available at <http://localhost:8000/docs>

## 📊 Expected Outputs

- Structured JSON with paragraph-level ministry labels
- Ministry frequency distribution
- Speaker-wise ministry statistics
- Time-based ministry coverage
- Visual charts and summary reports

> [!NOTE]
> For first time it may download the sentence-transformers model which can take some time.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📚 References

1. Rohit, Sakala & Singh, Navjyoti. (2018). Analysis of Speeches in Indian Parliamentary Debates. [10.48550/arXiv.1808.06834](https://arxiv.org/abs/1808.06834).
2. Wijeratne, Yudhanjaya & de Silva, Nisansa & Shanmugarasa, Yashothara. (2019). Natural Language Processing for Government: Problems and Potential. [Link](https://www.researchgate.net/publication/333968711_Natural_Language_Processing_for_Government_Problems_and_Potential)
3. Katre, Paritosh. (2019). NLP Based Text Analytics and Visualization of Political Speeches. International Journal of Recent Technology and Engineering. 8. 8574-8579. [10.35940/ijrte.C6503.098319](https://doi.org/10.35940/ijrte.C6503.098319).

## 👥 Team Members

1. Devadatta Mahesh Pokharanakar (142502012)
2. Chilaka Sri Krishna Sai (142502010)
3. Vaddi Govardhan (142502032)

## 📄 License

This project is for academic purposes as part of the NLP course.
