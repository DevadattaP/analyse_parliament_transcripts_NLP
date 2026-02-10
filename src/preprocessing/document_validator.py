import re
from typing import Dict, Any, Optional
from datetime import datetime
import langdetect
from langdetect import DetectorFactory

class DocumentValidator:
    """Validates and extracts metadata from parliamentary documents"""
    
    def __init__(self):
        DetectorFactory.seed = 0
        
    def validate_document(self, text: str, filename: str) -> Dict[str, Any]:
        """Main validation pipeline"""
        results = {
            'is_valid': False,
            'validation_errors': [],
            'metadata': {}
        }
        
        # 1. Language detection
        language = self.detect_language(text)
        if language != 'en':
            results['validation_errors'].append(f"Document not in English ({language})")
        
        # 2. Parliament content check
        is_parliament = self.is_parliament_content(text)
        if not is_parliament:
            results['validation_errors'].append("Document doesn't appear to be parliamentary content")
        
        # 3. Extract metadata
        metadata = self.extract_metadata(text, filename)
        results['metadata'] = metadata
        
        # 4. Determine if valid
        results['is_valid'] = (language == 'en' and is_parliament and 
                             metadata.get('house') is not None)
        
        return results
    
    def detect_language(self, text: str, sample_size=1000) -> str:
        """Detect document language"""
        sample = text[:sample_size]
        try:
            return langdetect.detect(sample)
        except:
            return "unknown"
    
    def is_parliament_content(self, text: str, threshold=0.005) -> bool:
        """Check if text contains parliamentary content"""
        parliament_keywords = [
            'parliament', 'loksabha', 'rajyasabha', 'honourable',
            'minister', 'member', 'speaker', 'debate', 'session',
            'question', 'answer', 'bill', 'act', 'budget', 'motion',
            'resolution', 'committee', 'parliamentary', 'proceeding'
        ]
        
        text_lower = text.lower()
        words = text_lower.split()
        if not words:
            return False
            
        keyword_count = sum(1 for keyword in parliament_keywords 
                          if keyword in text_lower)
        keyword_density = keyword_count / len(words)
        
        return keyword_density > threshold
    
    def extract_metadata(self, text: str, filename: str) -> Dict[str, Any]:
        """Extract metadata from document"""
        metadata = {
            'house': None,
            'doc_type': None,
            'date': None,
            'source_file': filename
        }
        
        # Extract house
        metadata['house'] = self.extract_house(text)
        
        # Extract document type
        metadata['doc_type'] = self.extract_document_type(text)
        
        # Extract date
        metadata['date'] = self.extract_date(text)
        
        return metadata
    
    def extract_house(self, text: str) -> Optional[str]:
        """Extract parliament house from text"""
        text_lower = text.lower()
        
        if any(term in text_lower for term in ['lok sabha', 'house of the people']):
            return 'Lok Sabha'
        elif any(term in text_lower for term in ['rajya sabha', 'council of states']):
            return 'Rajya Sabha'
        
        return None
    
    def extract_document_type(self, text: str) -> str:
        """Extract document type"""
        text_lower = text.lower()
        
        doc_types = {
            'budget': ['budget', 'finance bill', 'appropriation'],
            'debate': ['debate', 'discussion', 'motion'],
            'qna': ['question', 'answer', 'starred', 'unstarred'],
            'statement': ['statement', 'ministerial statement'],
            'bill': ['bill', 'act', 'legislation'],
            'other': []  # Default
        }
        
        for doc_type, keywords in doc_types.items():
            if any(keyword in text_lower for keyword in keywords):
                return doc_type
        
        return 'other'
    
    def extract_date(self, text: str) -> Optional[str]:
        """Extract date from document"""
        # Look for date patterns in first 500 chars
        sample = text[:500]
        
        date_patterns = [
            r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',
            r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}',
            r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, sample, re.IGNORECASE)
            if match:
                try:
                    # Try to parse the date
                    date_str = match.group()
                    # Add date parsing logic here
                    return date_str
                except:
                    continue
        
        return None
    
if __name__ == "__main__":
    # Example usage
    from src.preprocessing.pdf_extractor import *
    validator = DocumentValidator()
    file_name = "test.pdf"
    file_path = f"data/uploads/{file_name}"
    print(datetime.now())
    text = extract_text_from_pdf_file(file_path)
    results = validator.validate_document(text, file_path)
    print(results)
    print(datetime.now())
