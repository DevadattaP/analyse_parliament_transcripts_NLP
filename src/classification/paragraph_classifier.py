from __future__ import annotations

import ast
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
from sklearn.metrics.pairwise import cosine_similarity

from src.preprocessing.document_validator import DocumentValidator
from src.preprocessing.pdf_extractor import PDFExtractor

ClassificationMethod = Literal[
	"vocab",
	"ministry_embedding",
	"ministry_embedding_multi",
	"topic_embedding",
	"doc_word_topic",
]


@dataclass
class ClassificationConfig:
	"""Configuration for paragraph classification and optional baseline comparison."""

	pdf_path: str
	method: ClassificationMethod
	baseline_method: Optional[ClassificationMethod] = None
	reference_labels: Optional[Dict[int, str]] = None

	# Generic knobs
	skip_length: int = 10
	use_cleaning: bool = True
	validate_document: bool = True

	# Stopwords
	stopword_files: Sequence[str] = field(
		default_factory=lambda: (
			"data/stopwords/GBparl_stopwords-empirical.txt",
			"data/stopwords/stopwords.txt",
		)
	)

	# Validator vocab
	validator_vocab_path: str = "data/vocabulary/parliament_vocab.txt"

	# Classification assets
	vocab_file: str = "data/vocabulary/ministry_tfidf_vocab.json"
	ministry_embedding_file: str = "data/embeddings/ministry_embeddings.json"
	topic_embedding_file: str = "data/embeddings/topic_embeddings.json"
	topic_mapping_file: str = "data/topic_modeling/top_topics_per_ministry.csv"
	topic_state_file: str = "data/topic_modeling/state.csv"
	ministry_profiles_dir: str = "data/ministry_profiles"
	ministry_cluster_file: Optional[str] = None
	ministry_clusters: Optional[Dict[str, Any]] = None

	# Embedding model
	model_name: str = "all-MiniLM-L6-v2"
	model_cache_folder: str = "models"

	# Method-specific params
	primary_params: Dict[str, Any] = field(default_factory=dict)
	baseline_params: Dict[str, Any] = field(default_factory=dict)


def _resolve_path(path_str: str) -> Path:
	"""Resolve a path against the project root."""
	path = Path(path_str)
	if path.is_absolute():
		return path
	root = Path(__file__).resolve().parents[2]
	return root / path


def load_stopwords(custom_files: Sequence[str]) -> set[str]:
	"""Load sklearn + domain stopwords."""
	stopwords = set(ENGLISH_STOP_WORDS)

	for custom_file in custom_files:
		file_path = _resolve_path(custom_file)
		with file_path.open("r", encoding="utf-8") as file:
			for line in file:
				word = line.strip().lower()
				if word:
					stopwords.add(word)

	return stopwords


def clean_text(text: str, stopwords: Optional[set[str]] = None) -> str:
	"""Notebook-equivalent text cleaning function."""
	# Remove bullet characters.
	text = text.replace("\uf0b7", " ")

	# Remove numbering like "1." "2.".
	text = re.sub(r"\n?\d+\.\s*", " ", text)

	# Replace newlines with spaces.
	text = text.replace("\n", " ")

	# Remove multiple spaces.
	text = re.sub(r"\s+", " ", text)

	# Remove punctuation.
	text = re.sub(r"[^\w\s]", "", text)

	# Keep only alphabets.
	text = re.sub(r"[^a-zA-Z\s]", "", text)

	# Remove numbers.
	text = re.sub(r"\d+", " ", text)

	# Lowercase.
	text = text.lower()

	words = text.split()
	if stopwords:
		words = [word for word in words if word not in stopwords and len(word) > 2]

	# Remove duplicates while preserving order.
	seen = set()
	unique_words = []
	for word in words:
		if word not in seen:
			seen.add(word)
			unique_words.append(word)

	return " ".join(unique_words)


def extract_paragraphs(
	pdf_path: str,
	skip_length: int = 10,
	use_cleaning: bool = True,
	stopwords: Optional[set[str]] = None,
) -> Tuple[List[str], List[str], List[str]]:
	"""
	Extract paragraphs and speakers from PDF segments.

	Returns:
		cleaned_paragraphs, speakers, original_paragraphs
	"""
	extractor = PDFExtractor()
	result = extractor.extract(str(_resolve_path(pdf_path)))

	cleaned_paragraphs: List[str] = []
	speakers: List[str] = []
	original_paragraphs: List[str] = []

	for segment in result["segments"]:
		paragraph = segment.get("paragraph", "")
		if len(paragraph.split()) <= skip_length:
			continue

		normalized = clean_text(paragraph, stopwords) if use_cleaning else paragraph

		if not normalized.strip():
			continue

		cleaned_paragraphs.append(normalized)
		speakers.append(segment.get("speaker", "UNKNOWN"))
		original_paragraphs.append(paragraph)

	return cleaned_paragraphs, speakers, original_paragraphs


def validate(text: str, vocab_path: str) -> Dict[str, Any]:
	"""Validate full document text using the existing validator."""
	validator = DocumentValidator(vocab_path=str(_resolve_path(vocab_path)))
	return validator.validate_document(text)


def load_json(file_path: str) -> Dict[str, Any]:
	with _resolve_path(file_path).open("r", encoding="utf-8") as file:
		return json.load(file)


def load_embeddings(file_path: str) -> Dict[str, np.ndarray]:
	raw = load_json(file_path)
	return {key: np.array(value) for key, value in raw.items()}


def classify_vocab(paragraph: str, ministry_vocab: Dict[str, List[str]]) -> Dict[str, float]:
	"""Vocab-overlap classifier from notebook logic."""
	paragraph_lower = paragraph.lower()
	scores: Dict[str, float] = {}

	for ministry, vocab in ministry_vocab.items():
		count = 0
		for term in vocab:
			if term.lower() in paragraph_lower:
				count += 1
		scores[ministry] = float(count)

	total = sum(scores.values()) + 1e-9
	return {key: value / total for key, value in scores.items()}


def _softmax(score_map: Dict[str, float]) -> Dict[str, float]:
	if not score_map:
		return {}

	values = np.array(list(score_map.values()), dtype=float)
	values = values - np.max(values)
	exp_values = np.exp(values)
	probs = exp_values / (np.sum(exp_values) + 1e-12)
	return dict(zip(score_map.keys(), probs.tolist()))


def classify_ministry_embedding(
	paragraph: str,
	model: SentenceTransformer,
	ministry_embeddings: Dict[str, np.ndarray],
) -> Dict[str, float]:
	"""Single-vector-per-ministry embedding classifier."""
	paragraph_embedding = np.asarray(model.encode(paragraph), dtype=float)
	scores: Dict[str, float] = {}

	for ministry, ministry_embedding in ministry_embeddings.items():
		similarity = cosine_similarity(
			paragraph_embedding.reshape(1, -1), ministry_embedding.reshape(1, -1)
		)[0][0]
		scores[ministry] = float(similarity)

	return _softmax(scores)


def classify_ministry_embedding_multi(
	paragraph: str,
	model: SentenceTransformer,
	ministry_embeddings: Dict[str, np.ndarray],
	aggregation: Literal["max", "mean", "topk"] = "topk",
	top_k: int = 3,
) -> Dict[str, float]:
	"""Multi-vector ministry embedding classifier with configurable aggregation."""
	paragraph_embedding = np.asarray(model.encode(paragraph), dtype=float).reshape(1, -1)
	scores: Dict[str, float] = {}

	for ministry, ministry_vectors in ministry_embeddings.items():
		vectors = np.array(ministry_vectors)
		if vectors.ndim == 1:
			vectors = vectors.reshape(1, -1)

		similarities = cosine_similarity(paragraph_embedding, vectors)[0]

		if aggregation == "max":
			score = float(np.max(similarities))
		elif aggregation == "mean":
			score = float(np.mean(similarities))
		elif aggregation == "topk":
			k = max(1, min(top_k, len(similarities)))
			top_values = np.sort(similarities)[-k:]
			score = float(np.mean(top_values))
		else:
			raise ValueError("aggregation must be one of: 'max', 'mean', 'topk'")

		scores[ministry] = score

	return _softmax(scores)


def _parse_ministry_list(value: Any) -> List[str]:
	"""Safely parse ministry list values from CSV cells."""
	if isinstance(value, list):
		return [str(item).strip() for item in value if str(item).strip()]

	if value is None or (isinstance(value, float) and np.isnan(value)):
		return []

	text = str(value).strip()
	if not text:
		return []

	if text.startswith("[") and text.endswith("]"):
		try:
			parsed = ast.literal_eval(text)
			if isinstance(parsed, list):
				return [str(item).strip() for item in parsed if str(item).strip()]
		except (ValueError, SyntaxError):
			pass

	if "," in text:
		return [chunk.strip() for chunk in text.split(",") if chunk.strip()]

	return [text]


def load_topic_to_ministries(topic_mapping_file: str) -> Dict[str, List[str]]:
	"""Load topic -> ministries mapping from CSV."""
	topic_ministry_df = pd.read_csv(_resolve_path(topic_mapping_file))

	topic_to_ministries: Dict[str, List[str]] = {}
	for _, row in topic_ministry_df.iterrows():
		if "TopicID" in topic_ministry_df.columns:
			topic_id = str(row["TopicID"])
		elif "Topic" in topic_ministry_df.columns:
			topic_id = str(row["Topic"])
		else:
			continue

		ministries: List[str] = []
		if "Ministry" in topic_ministry_df.columns:
			ministries = _parse_ministry_list(row["Ministry"])
		elif "Ministries" in topic_ministry_df.columns:
			ministries = _parse_ministry_list(row["Ministries"])

		if ministries:
			topic_to_ministries[topic_id] = ministries

	return topic_to_ministries


def _topic_probs_to_ministry_probs(
	topic_probs: Dict[str, float],
	topic_to_ministries: Dict[str, List[str]],
) -> Dict[str, float]:
	"""Distribute topic probabilities across mapped ministries."""
	ministry_scores: Dict[str, float] = {}

	for topic, prob in topic_probs.items():
		ministries = topic_to_ministries.get(str(topic), [])
		if not ministries:
			continue

		share = prob / len(ministries)
		for ministry in ministries:
			ministry_scores[ministry] = ministry_scores.get(ministry, 0.0) + share

	total = sum(ministry_scores.values()) + 1e-12
	return {key: value / total for key, value in ministry_scores.items()}


def classify_topic_embedding(
	paragraph: str,
	model: SentenceTransformer,
	topic_embeddings: Dict[str, np.ndarray],
	topic_to_ministries: Dict[str, List[str]],
) -> Dict[str, float]:
	"""Topic-embedding classifier projected into ministry space."""
	paragraph_embedding = np.asarray(model.encode(paragraph), dtype=float)
	topic_scores: Dict[str, float] = {}

	for topic, topic_embedding in topic_embeddings.items():
		similarity = cosine_similarity(
			paragraph_embedding.reshape(1, -1), topic_embedding.reshape(1, -1)
		)[0][0]
		topic_scores[str(topic)] = float(similarity)

	topic_probs = _softmax(topic_scores)
	return _topic_probs_to_ministry_probs(topic_probs, topic_to_ministries)


def _load_ministry_names(ministry_profiles_dir: str) -> List[str]:
	"""Load ministry names from profile filenames."""
	profiles_path = _resolve_path(ministry_profiles_dir)
	return [filename[:-4] for filename in os.listdir(profiles_path) if filename.endswith(".txt")]


def _ensure_state_ministry_column(state_df: pd.DataFrame, ministry_profiles_dir: str) -> pd.DataFrame:
	"""Ensure state dataframe has a Ministry column, mapping from DocID when needed."""
	if "Ministry" in state_df.columns:
		return state_df.copy()

	if "DocID" not in state_df.columns:
		raise ValueError("state.csv must contain either 'Ministry' or 'DocID' column")

	ministry_names = _load_ministry_names(ministry_profiles_dir)
	if not ministry_names:
		raise ValueError("No ministry profiles found for DocID to Ministry mapping")

	state_copy = state_df.copy()

	def map_docid_to_ministry(doc_id: Any) -> str:
		idx = int(doc_id)
		if idx < 0 or idx >= len(ministry_names):
			raise ValueError(
				f"DocID index {idx} is out of range for {len(ministry_names)} ministry profiles"
			)
		return ministry_names[idx]

	state_copy["Ministry"] = state_copy["DocID"].apply(map_docid_to_ministry)
	return state_copy


def load_doc_word_topic_tables(
	state_file: str,
	ministry_profiles_dir: str,
) -> Dict[str, pd.DataFrame]:
	"""Build word-topic-doc probability tables from state.csv notebook method."""
	state_df = pd.read_csv(_resolve_path(state_file))
	state_df = _ensure_state_ministry_column(state_df, ministry_profiles_dir)

	if "Word" not in state_df.columns or "Topic" not in state_df.columns:
		raise ValueError("state.csv must contain 'Word' and 'Topic' columns")

	word_topic = pd.crosstab(state_df["Word"], state_df["Topic"], normalize="index")
	word_doc = pd.crosstab(state_df["Word"], state_df["Ministry"], normalize="index")
	topic_doc = pd.crosstab(state_df["Topic"], state_df["Ministry"], normalize="index")

	return {
		"word_topic": word_topic,
		"word_doc": word_doc,
		"topic_doc": topic_doc,
	}


def _preprocess_doc_word_topic_text(text: str) -> List[str]:
	"""Notebook-equivalent preprocess used by doc-word-topic classifier."""
	text = text.lower()
	text = re.sub(r"[^a-zA-Z\s]", "", text)
	return text.split()


def classify_doc_word_topic(
	paragraph: str,
	word_topic: pd.DataFrame,
	word_doc: pd.DataFrame,
	topic_doc: pd.DataFrame,
) -> Dict[str, float]:
	"""Non-Bayesian doc-word-topic probability classifier from notebook."""
	words = _preprocess_doc_word_topic_text(paragraph)
	scores: Dict[str, float] = {}

	common_topics = [topic for topic in word_topic.columns if topic in topic_doc.index]

	for word in words:
		if word not in word_doc.index or word not in word_topic.index:
			continue

		for ministry in word_doc.columns:
			p_doc_given_word = np.asarray(word_doc.at[word, ministry], dtype=float).item()
			topic_sum = 0.0
			for topic in common_topics:
				p_word_given_topic = np.asarray(word_topic.at[word, topic], dtype=float).item()
				p_topic_given_doc = np.asarray(topic_doc.at[topic, ministry], dtype=float).item()
				topic_sum += p_word_given_topic * p_topic_given_doc

			scores[ministry] = scores.get(ministry, 0.0) + (p_doc_given_word * topic_sum)

	if not scores:
		uniform = 1.0 / max(1, len(word_doc.columns))
		return {ministry: round(uniform, 4) for ministry in word_doc.columns}

	total = sum(scores.values()) + 1e-9
	return {key: round(value / total, 4) for key, value in scores.items()}


def _top_k_labels(distribution: Dict[str, float], k: int) -> List[str]:
	return [
		key
		for key, _ in sorted(distribution.items(), key=lambda item: item[1], reverse=True)[:k]
	]


def _to_aligned_vectors(
	first: Dict[str, float],
	second: Dict[str, float],
	epsilon: float = 1e-12,
) -> Tuple[np.ndarray, np.ndarray, List[str]]:
	labels = sorted(set(first.keys()) | set(second.keys()))
	f = np.array([first.get(label, 0.0) for label in labels], dtype=float)
	s = np.array([second.get(label, 0.0) for label in labels], dtype=float)

	f = f + epsilon
	s = s + epsilon

	f = f / np.sum(f)
	s = s / np.sum(s)

	return f, s, labels


def _normalize_ministry_clusters(cluster_data: Dict[str, Any]) -> Dict[str, str]:
	"""
	Normalize cluster data to ministry -> cluster_id mapping.

	Supported formats:
	1. {"Ministry_A": "cluster_1", "Ministry_B": "cluster_2"}
	2. {"cluster_1": ["Ministry_A", "Ministry_C"], "cluster_2": ["Ministry_B"]}
	"""
	if not cluster_data:
		return {}

	# ministry -> cluster format
	if all(not isinstance(value, (list, tuple, set, dict)) for value in cluster_data.values()):
		return {str(ministry): str(cluster) for ministry, cluster in cluster_data.items()}

	# cluster -> ministries format
	ministry_to_cluster: Dict[str, str] = {}
	for cluster_name, ministries in cluster_data.items():
		if isinstance(ministries, (list, tuple, set)):
			for ministry in ministries:
				ministry_to_cluster[str(ministry)] = str(cluster_name)

	return ministry_to_cluster


def _normalize_reference_labels(reference_labels: Dict[Any, Any]) -> Dict[int, str]:
	"""Normalize paragraph-index labels to an int -> ministry mapping."""
	normalized: Dict[int, str] = {}
	for paragraph_id, ministry in reference_labels.items():
		try:
			index = int(paragraph_id)
		except (TypeError, ValueError) as exc:
			raise ValueError(f"Reference label key {paragraph_id!r} is not a valid paragraph index") from exc

		label = str(ministry).strip()
		if not label:
			raise ValueError(f"Reference label for paragraph {index} is empty")

		normalized[index] = label

	return normalized


def _build_reference_distributions(
	reference_labels: Dict[Any, Any],
	paragraph_count: int,
) -> List[Dict[str, float]]:
	"""Convert paragraph index labels into one-hot distributions for evaluation."""
	normalized_labels = _normalize_reference_labels(reference_labels)
	missing_indices = [idx for idx in range(paragraph_count) if idx not in normalized_labels]
	if missing_indices:
		raise ValueError(
			"reference_labels is missing labels for paragraph indices: "
			+ ", ".join(str(idx) for idx in missing_indices)
		)

	extra_indices = sorted(idx for idx in normalized_labels if idx >= paragraph_count or idx < 0)
	if extra_indices:
		raise ValueError(
			"reference_labels contains out-of-range paragraph indices: "
			+ ", ".join(str(idx) for idx in extra_indices)
		)

	return [{normalized_labels[idx]: 1.0} for idx in range(paragraph_count)]


def _build_ministry_to_topics(topic_to_ministries: Dict[str, List[str]]) -> Dict[str, set[str]]:
	"""Build reverse mapping ministry -> set(topics)."""
	ministry_to_topics: Dict[str, set[str]] = {}
	for topic, ministries in topic_to_ministries.items():
		for ministry in ministries:
			if ministry not in ministry_to_topics:
				ministry_to_topics[ministry] = set()
			ministry_to_topics[ministry].add(str(topic))
	return ministry_to_topics


def _get_cluster_group_ministries(
	predicted_ministry: str,
	ministry_to_cluster: Optional[Dict[str, str]],
) -> List[str]:
	"""Return all ministries that share the predicted ministry's cluster."""
	if not ministry_to_cluster:
		return []

	cluster_id = ministry_to_cluster.get(predicted_ministry)
	if cluster_id is None:
		return []

	return sorted(
		ministry
		for ministry, mapped_cluster in ministry_to_cluster.items()
		if mapped_cluster == cluster_id
	)


def _get_topic_group_ministries(
	predicted_ministry: str,
	topic_to_ministries: Optional[Dict[str, List[str]]],
) -> List[str]:
	"""Return all ministries that share at least one topic with the predicted ministry."""
	if not topic_to_ministries:
		return []

	ministry_to_topics = _build_ministry_to_topics(topic_to_ministries)
	topics = ministry_to_topics.get(predicted_ministry, set())
	if not topics:
		return []

	topic_group: set[str] = set()
	for topic, ministries in topic_to_ministries.items():
		if str(topic) in topics:
			topic_group.update(str(ministry) for ministry in ministries)

	return sorted(topic_group)


def compare_distributions(
	primary_outputs: Sequence[Dict[str, float]],
	baseline_outputs: Sequence[Dict[str, float]],
	top_k: int = 3,
) -> Dict[str, float]:
	return compare_distributions_with_context(
		primary_outputs=primary_outputs,
		baseline_outputs=baseline_outputs,
		ministry_to_cluster=None,
		topic_to_ministries=None,
	)


def compare_distributions_with_context(
	primary_outputs: Sequence[Dict[str, float]],
	baseline_outputs: Sequence[Dict[str, float]],
	ministry_to_cluster: Optional[Dict[str, str]] = None,
	topic_to_ministries: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, float]:
	"""
	Compare primary predictions against baseline (treated as actual labels).

	Reported metrics focus on count-based agreement/error analysis:
	- exact matches
	- top-2..top-5 errors (wrong top-1 but actual appears in predicted top-k)
	- same-cluster matches (if cluster mapping provided)
	- same-topic-family matches (if topic mapping provided and cluster mapping not provided)
	"""
	if len(primary_outputs) != len(baseline_outputs):
		raise ValueError("primary_outputs and baseline_outputs must have same length")

	if not primary_outputs:
		return {
			"num_paragraphs": 0,
			"exact_match_count": 0,
			"exact_match_rate": 0.0,
			"top2_error_count": 0,
			"top3_error_count": 0,
			"top4_error_count": 0,
			"top5_error_count": 0,
			"top2_error_rate": 0.0,
			"top3_error_rate": 0.0,
			"top4_error_rate": 0.0,
			"top5_error_rate": 0.0,
			"same_cluster_match_count": 0,
			"same_cluster_match_rate": 0.0,
			"same_topic_family_match_count": 0,
			"same_topic_family_match_rate": 0.0,
		}

	exact_match_count = 0
	topk_error_counts: Dict[int, int] = {2: 0, 3: 0, 4: 0, 5: 0}
	same_cluster_match_count = 0
	same_topic_family_match_count = 0

	ministry_to_topics = (
		_build_ministry_to_topics(topic_to_ministries)
		if topic_to_ministries is not None
		else None
	)

	for primary_dist, baseline_dist in zip(primary_outputs, baseline_outputs):
		primary_top = _top_k_labels(primary_dist, 1)
		baseline_top = _top_k_labels(baseline_dist, 1)
		if not primary_top or not baseline_top:
			continue

		predicted = primary_top[0]
		actual = baseline_top[0]

		if predicted == actual:
			exact_match_count += 1
		else:
			for k in (2, 3, 4, 5):
				if actual in _top_k_labels(primary_dist, k):
					topk_error_counts[k] += 1

		if ministry_to_cluster is not None:
			predicted_cluster = ministry_to_cluster.get(predicted)
			actual_cluster = ministry_to_cluster.get(actual)
			if (
				predicted_cluster is not None
				and actual_cluster is not None
				and predicted_cluster == actual_cluster
			):
				same_cluster_match_count += 1
		if ministry_to_topics is not None:
			predicted_topics = ministry_to_topics.get(predicted, set())
			actual_topics = ministry_to_topics.get(actual, set())
			if predicted_topics and actual_topics and predicted_topics.intersection(actual_topics):
				same_topic_family_match_count += 1

	total = len(primary_outputs)
	return {
		"num_paragraphs": total,
		"exact_match_count": exact_match_count,
		"exact_match_rate": exact_match_count / total,
		"top2_error_count": topk_error_counts[2],
		"top3_error_count": topk_error_counts[3],
		"top4_error_count": topk_error_counts[4],
		"top5_error_count": topk_error_counts[5],
		"top2_error_rate": topk_error_counts[2] / total,
		"top3_error_rate": topk_error_counts[3] / total,
		"top4_error_rate": topk_error_counts[4] / total,
		"top5_error_rate": topk_error_counts[5] / total,
		"same_cluster_match_count": same_cluster_match_count,
		"same_cluster_match_rate": same_cluster_match_count / total,
		"same_topic_family_match_count": same_topic_family_match_count,
		"same_topic_family_match_rate": same_topic_family_match_count / total,
	}


def _build_method_assets(method: ClassificationMethod, config: ClassificationConfig) -> Dict[str, Any]:
	"""Load only files needed for the chosen method."""
	assets: Dict[str, Any] = {}

	if method == "vocab":
		assets["ministry_vocab"] = load_json(config.vocab_file)
	elif method == "ministry_embedding":
		assets["ministry_embeddings"] = load_embeddings(config.ministry_embedding_file)
	elif method == "ministry_embedding_multi":
		assets["ministry_embeddings"] = load_embeddings(config.ministry_embedding_file)
	elif method == "topic_embedding":
		assets["topic_embeddings"] = load_embeddings(config.topic_embedding_file)
		assets["topic_to_ministries"] = load_topic_to_ministries(config.topic_mapping_file)
	elif method == "doc_word_topic":
		assets.update(
			load_doc_word_topic_tables(
				state_file=config.topic_state_file,
				ministry_profiles_dir=config.ministry_profiles_dir,
			)
		)
	else:
		raise ValueError(f"Unsupported method: {method}")

	return assets


def _requires_embedding_model(method: ClassificationMethod) -> bool:
	return method in {"ministry_embedding", "ministry_embedding_multi", "topic_embedding"}


def _classify_with_method(
	paragraph: str,
	method: ClassificationMethod,
	assets: Dict[str, Any],
	model: Optional[SentenceTransformer],
	method_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, float]:
	params = method_params or {}

	if method == "vocab":
		return classify_vocab(paragraph, assets["ministry_vocab"])

	if method == "ministry_embedding":
		if model is None:
			raise ValueError("Embedding model is required for ministry_embedding")
		return classify_ministry_embedding(paragraph, model, assets["ministry_embeddings"])

	if method == "ministry_embedding_multi":
		if model is None:
			raise ValueError("Embedding model is required for ministry_embedding_multi")
		aggregation = params.get("aggregation", "topk")
		top_k = int(params.get("top_k", 3))
		return classify_ministry_embedding_multi(
			paragraph,
			model,
			assets["ministry_embeddings"],
			aggregation=aggregation,
			top_k=top_k,
		)

	if method == "topic_embedding":
		if model is None:
			raise ValueError("Embedding model is required for topic_embedding")
		return classify_topic_embedding(
			paragraph,
			model,
			assets["topic_embeddings"],
			assets["topic_to_ministries"],
		)

	if method == "doc_word_topic":
		return classify_doc_word_topic(
			paragraph,
			assets["word_topic"],
			assets["word_doc"],
			assets["topic_doc"],
		)

	raise ValueError(f"Unsupported method: {method}")


def run_classification_pipeline(config: ClassificationConfig) -> Dict[str, Any]:
	"""Run the end-to-end classification pipeline with optional baseline."""
	stopwords = load_stopwords(config.stopword_files)

	paragraphs, speakers, original_paragraphs = extract_paragraphs(
		config.pdf_path,
		skip_length=config.skip_length,
		use_cleaning=config.use_cleaning,
		stopwords=stopwords,
	)

	validation: Optional[Dict[str, Any]] = None
	if config.validate_document:
		full_text = "\n\n".join(paragraphs)
		validation = validate(full_text, vocab_path=config.validator_vocab_path)
		if not validation.get("is_valid", False):
			return {
				"config": config.__dict__,
				"validation": validation,
				"num_paragraphs": len(paragraphs),
				"results": [],
				"metrics": None,
			}

	primary_assets = _build_method_assets(config.method, config)
	baseline_assets = (
		_build_method_assets(config.baseline_method, config)
		if config.baseline_method
		else None
	)
	ministry_to_cluster: Optional[Dict[str, str]] = None
	if config.ministry_clusters is not None:
		ministry_to_cluster = _normalize_ministry_clusters(config.ministry_clusters)
	elif config.ministry_cluster_file:
		cluster_data = load_json(config.ministry_cluster_file)
		ministry_to_cluster = _normalize_ministry_clusters(cluster_data)

	topic_to_ministries_for_output: Optional[Dict[str, List[str]]] = None
	if config.topic_mapping_file:
		topic_mapping_path = _resolve_path(config.topic_mapping_file)
		if topic_mapping_path.exists():
			topic_to_ministries_for_output = load_topic_to_ministries(config.topic_mapping_file)

	reference_distributions = (
		_build_reference_distributions(config.reference_labels, len(paragraphs))
		if config.reference_labels is not None
		else None
	)

	needs_model = _requires_embedding_model(config.method) or (
		config.baseline_method is not None
		and _requires_embedding_model(config.baseline_method)
	)
	model = (
		SentenceTransformer(
			config.model_name,
			cache_folder=str(_resolve_path(config.model_cache_folder)),
		)
		if needs_model
		else None
	)

	results: List[Dict[str, Any]] = []
	primary_distributions: List[Dict[str, float]] = []
	baseline_distributions: List[Dict[str, float]] = []

	for idx, paragraph in enumerate(paragraphs):
		primary_dist = _classify_with_method(
			paragraph,
			config.method,
			primary_assets,
			model,
			config.primary_params,
		)

		baseline_dist = None
		if config.baseline_method and baseline_assets is not None:
			baseline_dist = _classify_with_method(
				paragraph,
				config.baseline_method,
				baseline_assets,
				model,
				config.baseline_params,
			)

		primary_distributions.append(primary_dist)
		if baseline_dist is not None:
			baseline_distributions.append(baseline_dist)

		reference_dist = reference_distributions[idx] if reference_distributions is not None else None

		result_row: Dict[str, Any] = {
			"paragraph_id": idx,
			"speaker": speakers[idx],
			"paragraph": paragraph,
			"original_paragraph": original_paragraphs[idx],
			"primary_distribution": primary_dist,
			"primary_top3": _top_k_labels(primary_dist, 3),
		}

		if baseline_dist is not None:
			result_row["baseline_distribution"] = baseline_dist
			result_row["baseline_top3"] = _top_k_labels(baseline_dist, 3)

		if reference_dist is not None:
			result_row["reference_distribution"] = reference_dist
			result_row["reference_label"] = _top_k_labels(reference_dist, 1)[0]

		predicted_ministry = _top_k_labels(primary_dist, 1)[0] if primary_dist else None
		result_row["predicted_ministry"] = predicted_ministry
		result_row["cluster_group_ministries"] = (
			_get_cluster_group_ministries(predicted_ministry, ministry_to_cluster)
			if predicted_ministry is not None
			else []
		)
		result_row["topic_group_ministries"] = (
			_get_topic_group_ministries(predicted_ministry, topic_to_ministries_for_output)
			if predicted_ministry is not None
			else []
		)

		results.append(result_row)

	metrics = None
	evaluation_distributions: Optional[List[Dict[str, float]]] = None
	if reference_distributions is not None:
		evaluation_distributions = reference_distributions
	elif config.baseline_method:
		evaluation_distributions = baseline_distributions

	if evaluation_distributions is not None:
		topic_methods = {"topic_embedding", "doc_word_topic"}
		use_topic_family_match = (
			config.reference_labels is not None
			or config.method in topic_methods
			or (config.baseline_method in topic_methods if config.baseline_method else False)
		)

		topic_to_ministries_for_metrics: Optional[Dict[str, List[str]]] = None
		if use_topic_family_match:
			topic_to_ministries_for_metrics = load_topic_to_ministries(config.topic_mapping_file)

		metrics = compare_distributions_with_context(
			primary_distributions,
			evaluation_distributions,
			ministry_to_cluster=ministry_to_cluster,
			topic_to_ministries=topic_to_ministries_for_metrics,
		)

	return {
		"config": config.__dict__,
		"validation": validation,
		"num_paragraphs": len(paragraphs),
		"results": results,
		"metrics": metrics,
	}


def save_results(output: Dict[str, Any], output_file: str) -> None:
	"""Save pipeline output as JSON."""
	output_path = _resolve_path(output_file)
	output_path.parent.mkdir(parents=True, exist_ok=True)

	with output_path.open("w", encoding="utf-8") as file:
		json.dump(output, file, indent=4, ensure_ascii=False)


if __name__ == "__main__":
	# Example usage
	cfg = ClassificationConfig(
		pdf_path="data/uploads/test.pdf",
		method="ministry_embedding_multi",
		baseline_method="vocab",
		ministry_embedding_file="data/embeddings/ministry_embeddings3.json",
		primary_params={"aggregation": "topk", "top_k": 3},
	)

	output = run_classification_pipeline(cfg)
	print(json.dumps({"metrics": output.get("metrics")}, indent=4))
