from typing import Dict, Any, List
import langdetect
from langdetect import DetectorFactory
from src.preprocessing.pdf_extractor import PDFExtractor
import json

class DocumentValidator:
    """Validates and extracts metadata from parliamentary documents"""
    
    def __init__(self, vocab_path: str = "data/vocabulary/parliament_vocab.txt", vocab_threshold: int = 5):
        DetectorFactory.seed = 42
        self.vocab_path = vocab_path
        self.vocab_threshold = vocab_threshold
        self._load_parliament_vocab()
        
    def _load_parliament_vocab(self):
        """Load parliamentary vocabulary for content validation"""
        with open(self.vocab_path, "r", encoding="utf-8") as f:
            self.vocab = [line.strip().lower() for line in f.readlines()]
            
    def validate_document(self, text: str) -> Dict[str, Any]:
        """Main validation pipeline"""
        results = {
            'is_valid': False,
            'is_english': False,
            'validation_errors': [],
            'vocab_size': len(self.vocab),
            'required_vocab_matches': self.vocab_threshold,
        }
        try:
            # 1. Language detection
            language = self.detect_language(text)
            if language != 'en':
                results['validation_errors'].append(f"Document not in English but in {language}")
            else:
                results['is_english'] = True
            
            # 2. Parliament content check (with improved method)
            is_parliament, matches = self.is_parliament_content(text, threshold=self.vocab_threshold)
            confidence = len(matches) / len(self.vocab) if self.vocab else 0
            if not is_parliament:
                results['validation_errors'].append(
                    f"Document doesn't appear to be parliamentary content (confidence: {confidence:.2f})"
                )
            # Add confidence score
            results['parliament_confidence'] = confidence
            
            results['matched_vocab_terms'] = matches
                    
            # 4. Determine if valid (more lenient criteria)
            results['is_valid'] = language == 'en' and is_parliament        
        except Exception as e:
            results['validation_errors'].append(f"Error during validation: {str(e)}")
        
        return results
    
    def detect_language(self, text: str, sample_size=2000) -> str:
        """Detect document language with better sampling"""
        # Take samples from beginning, middle, and end
        text_length = len(text)
        if text_length > sample_size * 3:
            samples = [
                text[:sample_size],
                text[text_length//2 - sample_size//2:text_length//2 + sample_size//2],
                text[-sample_size:]
            ]
            sample = ' '.join(samples)
        else:
            sample = text
        
        try:
            return langdetect.detect(sample)
        except:
            return "unknown"
    
    def is_parliament_content(self, text: str, threshold: int = 5) -> tuple[bool, List[str]]:
        """Check if text contains parliamentary content with confidence score"""
        text_lower = text.lower()
        matches = [term for term in self.vocab if term.lower() in text_lower]
        return len(matches)>= threshold, matches
        

if __name__ == "__main__":
    # Test with the provided PDF
    
    validator = DocumentValidator()
    file_name = "test.pdf"
    file_path = f"data/uploads/{file_name}"
    
    print(f"Processing: {file_path}")
    print("-" * 50)
    
    # Extract text
    extractor = PDFExtractor()
    result = extractor.extract(file_path)
    text = "\n\n".join([seg["paragraph"] for seg in result["segments"]])
    
    # Validate
    results = validator.validate_document(text)
    
    # Print results nicely
    print("VALIDATION RESULTS:")
    print(json.dumps(results, indent=4))
    