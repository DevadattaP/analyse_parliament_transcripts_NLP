# Indian Parliamentary Proceedings NLP Analysis

## 📋 Project Description

This project aims to analyze Indian parliamentary proceedings transcripts using Natural Language Processing (NLP) techniques. The system processes parliamentary session documents (budget speeches, bill introductions, Q&A sessions, debates, ministerial statements) to extract structured information including speaker identification, topic detection, named entity recognition, sentiment analysis, and automated summarization.

## 🎯 Key Features

- **PDF Processing:** Convert parliamentary PDFs to structured text
- **Speaker Identification:** Detect speakers, roles, parties, and ministries
- **Named Entity Recognition:** Extract people, places, schemes, ministries, bills, and monetary values
- **Topic Modeling:** Segment discussions into policy areas (agriculture, taxation, etc.)
- **Sentiment Analysis:** Classify statements into categories (Appreciate, Neutral, Call for Action, etc.)
- **Summarization:** Generate topic-wise and speaker-wise summaries
- **Visualization:** Produce timelines, statistics, and analytical dashboards

## Project Structure

```bash
parliament-nlp-analysis/
├── documentation/         # Project documentation and reports
├── data/
│   ├── raw/               # Original PDF documents
│   ├── processed/         # Processed text files
│   ├── annotated/         # Manually annotated datasets
│   └── outputs/           # Generated outputs (JSON, visualizations)
├── src/
│   ├── preprocessing/     # PDF to text conversion, cleaning
│   ├── speaker_id/        # Speaker identification models
│   ├── ner/               # Named Entity Recognition
│   ├── topic_modeling/    # Topic segmentation and classification
│   ├── sentiment/         # Sentiment and stance analysis
│   ├── summarization/     # Extractive and abstractive summarization
│   ├── visualization/     # Data visualization modules
│   └── api/               # FastAPI web service
├── notebooks/             # Jupyter notebooks for experimentation
├── tests/                 # Unit and integration tests
├── models/                # Saved models and checkpoints
├── requirements.txt       # Python dependencies
├── config.yaml            # Configuration file
└── README.md              # This file
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

### Start Web API

```bash
uvicorn src.api.main:app --reload
```

The FastAPI server will start at <http://localhost:8000>

API documentation is available at <http://localhost:8000/docs>

## 📊 Expected Outputs

- **Structured JSON:** Processed data in machine-readable format
- **Summary Reports:** Topic-wise and speaker-wise summaries
- **Visual Analytics:** Charts, timelines, and statistical overviews
- **API Endpoints:** RESTful services for programmatic access

## 🧪 Testing

Run unit tests using pytest:

```bash
pytest tests/
```

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
