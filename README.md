# 🇮🇳 Indian Parliamentary Proceedings – Ministry Classification & Analytics

## 📋 Project Description

This project presents a comprehensive NLP-based analysis of Indian parliamentary proceedings, with a focus on **automatically identifying the ministry being discussed at the paragraph level**.

Unlike standard supervised classification tasks, this work operates in a **low-resource setting without annotated ground truth labels**. To address this, we explore and compare multiple unsupervised and weakly supervised approaches for ministry classification.

The project goes beyond a single-model solution and systematically evaluates a range of techniques, including:

- Lexical methods (TF-IDF, vocabulary matching)
- Semantic embedding-based methods (Sentence-BERT variants)
- Topic modeling approaches
- Hybrid probabilistic scoring methods

In addition to classification, the system provides tools for analyzing parliamentary discussions through:

- ministry-wise distributions
- speaker-wise analysis
- topic-level insights

The goal is to understand how different NLP paradigms perform in **real-world, noisy, domain-specific political text** under minimal supervision.

## 🎯 Core Objectives

- Process raw parliamentary PDFs into structured textual data
- Segment documents into meaningful units (speaker turns and paragraphs)
- Explore multiple NLP approaches for ministry classification, including:
  - TF-IDF-based methods
  - Embedding-based semantic similarity
  - Topic modeling
  - Probabilistic scoring techniques
- Evaluate classification performance **without ground truth labels** using weak supervision
- Compare strengths, limitations, and assumptions of different methods
- Analyze ministry distributions across documents and speakers
- Provide structured outputs and visualizations for downstream analysis

## 🧠 Main NLP Task

The core task is framed as a **paragraph-level multi-class classification problem**, where each paragraph is assigned to one of 53 ministries of the Government of India.

However, unlike traditional classification settings:

- No labeled dataset is available
- Ministries may have overlapping semantic domains
- Parliamentary language is highly contextual and diverse

To address this, we treat the task as a **weakly supervised and similarity-driven classification problem**, where:

- Paragraphs are compared against ministry representations
- Multiple scoring strategies are used to infer relevance
- Evaluation is performed using **LLM-generated reference labels** and cross-method agreement

This setup allows us to study how different representations (lexical, semantic, topical) capture the notion of “ministry relevance”.

## ⚙️ System Architecture

The system follows a modular NLP pipeline combining preprocessing, representation learning, and multi-method classification:

### 1. Preprocessing

- Convert PDF documents into raw text
- Remove headers, footers, and formatting noise
- Segment text into paragraphs and speaker turns
- Normalize and clean textual content

### 2. Text Representation

Different representations of text are constructed to support multiple methods:

- **Lexical features**: TF-IDF, curated vocabulary
- **Semantic embeddings**: Sentence-BERT (all-MiniLM-L6-v2)
- **Topic distributions**: Topic modeling using external tools

### 3. Ministry Classification (Multiple Methods)

Each paragraph is classified using several independent approaches:

- **TF-IDF similarity**
- **Vocabulary-based scoring**
- **Embedding similarity (single document embedding)**
- **Embedding averaging (mean of paragraph embeddings per ministry)**
- **Top-k embedding similarity aggregation**
- **Topic-based classification**
- **Doc–Word–Topic probabilistic scoring (custom heuristic)**

Each method produces:

- A ranked list of candidate ministries
- A confidence distribution over all ministries

### 4. Evaluation Framework (Weak Supervision)

Since no labeled data is available:

- Reference labels are generated using an LLM under controlled prompting
- Methods are compared using:
  - Exact match accuracy
  - Top-k inclusion metrics
  - Cluster-level agreement
  - Topic-family alignment

### 5. Analysis and Visualization

- Ministry distribution across documents
- Speaker-wise ministry engagement
- Embedding space visualization (PCA, t-SNE)
- Comparative analysis of different methods

The goal is not just prediction, but understanding:

- when each method works
- where it fails
- what assumptions it relies on

This architecture enables both **practical analysis of parliamentary data** and **systematic evaluation of NLP methods under weak supervision**.

## 🧠 Key Insights

- Averaging paragraph embeddings provides a strong and stable ministry representation
- Semantic embeddings outperform purely lexical methods in most cases
- Topic modeling captures high-level themes but lacks fine-grained discrimination
- Probabilistic combinations of signals can improve interpretability but rely on strong assumptions
- Evaluation without labels is feasible using weak supervision and agreement-based metrics

## ⚠️ Limitations

- No ground-truth labeled dataset is available
- LLM-generated labels are used as weak reference signals
- Ministries may overlap semantically, making classification ambiguous
- Topic modeling depends on external tools and parameter choices

---

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

## � How It Works

### 1. Document Upload

- Navigate to `/upload/` in your browser
- Drag-and-drop a PDF file or click to browse and select a parliamentary PDF
- Click **"Start Classification"** button
- The file is uploaded to the backend and a unique task ID is generated immediately
- The browser displays the task ID and begins polling for progress

### 2. Backend Processing

Once uploaded, the backend processes the document asynchronously:

**Stage 1: Document Parsing**

- Extract text from PDF and segment into paragraphs
- Identify speaker names and roles
- Clean and preprocess text (remove noise, normalize whitespace)

**Stage 2: Paragraph Classification (7 Methods Run in Sequence)**
Each paragraph is classified using all 7 methods:

1. **vocab** - Keyword-based vocabulary matching
2. **doc_word_topic** - Document-word-topic probabilistic classification
3. **ministry_embedding** - Semantic similarity using embedding
4. **ministry_embedding_v1** - Semantic similarity using embedding (full ministry -> one embedding)
5. **ministry_embedding_v2** - Semantic similarity using embedding (average of all paragraph embeddings for ministry)
6. **ministry_embedding_multi** - Multi-embedding aggregation (top-k similar paragraph embeddings for each ministry)
7. **topic_embedding** - Topic-embeddings similarity and topic-ministry mapping

For each method:

- The paragraph is compared against official ministry profiles
- A confidence distribution across all ministries is computed
- The top ministry prediction and confidence score are recorded

**Stage 3: Result Aggregation**

- Results from all 7 methods are collected
- Each result includes: paragraph ID, speaker, original & processed text, predicted ministry, and full confidence distribution across all ministries

### 3. Real-Time Progress Display

As methods execute in the backend:

- Progress bar animates from 0% → 100%
- Text shows "X/7 methods completed" updating every 2 seconds
- When complete, the results panel appears

### 4. Interactive Results Display

**Results Table (Per Method):**

- Click any method tab to view that method's results
- Table columns: Paragraph ID | Text Preview | Predicted Ministry | Confidence
- Shows first 100 paragraphs per method

**Row Details Modal:**

- Click on any row to open a detailed modal
- Shows:
  - Paragraph ID
  - Speaker name
  - Original paragraph text (unprocessed)
  - Processed paragraph text (cleaned)
  - Predicted ministry (from this method)
  - All ministries ranked by confidence scores

**Compare Button:**

- Click "Compare" in the detail modal to open comparison view
- Shows predictions from all 7 methods for the same paragraph
- Displays:
  - Paragraph ID, original text, processed text
  - Method-wise predictions with confidence scores
  - Side-by-side comparison of all 7 methods

### 5. Output Structure

Each result includes:

```json
{
  "paragraph_id": 42,
  "speaker": "Speaker Name",
  "original_paragraph": "Raw text from PDF...",
  "paragraph": "Cleaned and processed text...",
  "predicted_ministry": "Ministry_of_Finance_MoF_",
  "primary_distribution": {
    "Ministry_of_Finance_MoF_": 0.8521,
    "Ministry_of_Commerce_and_Industry_MoCI_": 0.0342,
    "Ministry_of_Power_MoP_": 0.0198,
    ...
  }
}
```

All results are returned as JSON and displayed in interactive tables in the browser.

> [!NOTE]
> For first time execution, the system will download the sentence-transformers model which can take some time. Subsequent uploads will be faster.

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

> This project is for academic purposes as part of the NLP course (DS5601), Department of Data Science, IIT Palakkad
---
