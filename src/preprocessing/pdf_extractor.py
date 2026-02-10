import io
import re
import pdfplumber
import PyPDF2
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class ExtractedText:
    """Data class for extracted text with metadata"""
    raw_text: str
    cleaned_text: str
    pages: List[str]
    page_count: int
    metadata: Dict[str, Any]
    speaker_segments: List[Dict[str, Any]] = None
    
class PDFExtractor:
    """Extract and clean text from parliamentary PDF documents"""
    
    def __init__(self, use_pdfplumber: bool = True):
        """
        Initialize PDF extractor
        
        Args:
            use_pdfplumber: Use pdfplumber for better text extraction (recommended)
                           If False, uses PyPDF2
        """
        self.use_pdfplumber = use_pdfplumber
        self._setup_patterns()
        
    def _setup_patterns(self):
        """Setup regex patterns for cleaning parliamentary PDFs"""
        # Page headers/footers patterns (common in Indian parliamentary documents)
        self.header_patterns = [
            r'^\s*LOK\s+SABHA\s*$',
            r'^\s*RAJYA\s+SABHA\s*$',
            r'^\s*UNSTARRED\s+QUESTION\s+NO\.?\s*\d+',
            r'^\s*STARRED\s+QUESTION\s+NO\.?\s*\d+',
            r'^\s*\d+\s+TH\s+LOK\s+SABHA',
            r'^\s*\d+\s+TH\s+RAJYA\s+SABHA',
            r'^\s*PARLIAMENT\s+OF\s+INDIA',
            r'^\s*MINISTRY\s+OF\s+[A-Z\s]+',
        ]
        
        # Page number patterns
        self.page_num_patterns = [
            r'^\s*\d+\s*$',
            r'^\s*Page\s+\d+\s+of\s+\d+\s*$',
            r'^\s*\d+\s*/\s*\d+\s*$',
            r'^\s*\[\s*\d+\s*\]\s*$',
        ]
        
        # Date patterns
        self.date_patterns = [
            r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',
            r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}',
            r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}',
            r'\d{4}-\d{2}-\d{2}',  # ISO format
        ]
        
        # Speaker patterns (Indian parliamentary conventions)
        self.speaker_patterns = [
            # Indian honorifics
            r'^(?:SHRI|SHRIMATI|DR\.|MR\.|MRS\.|MS\.|HON\'BLE|HONOURABLE)\s+([A-Z][A-Z\s\.\-]+?)(?:\s*[\(:,\-]|\s*$)',
            # Speaker titles
            r'^(?:The\s+)?(?:Minister|Speaker|Deputy\s+Speaker|Chairman|Chairperson|Leader)\s+(?:of\s+[A-Za-z\s]+)?(?:[A-Z][A-Za-z\s]+?)(?:\s*[\(:,\-]|\s*$)',
            # Name in parentheses
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s*\([^)]+\)(?:\s*[:,\-]|\s*$)',
            # Simple name with colon
            r'^([A-Z][A-Z\s\.]+?)\s*:\s',
        ]
        
        # Time patterns in transcripts
        self.time_patterns = [
            r'\d{1,2}:\d{2}\s*(?:[APap][Mm])?',
            r'\d{1,2}\.\d{2}\s*[APap][Mm]',
        ]
        
    def extract_from_file(self, file_path: str) -> ExtractedText:
        """
        Extract text from PDF file
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            ExtractedText object with raw and cleaned text
        """
        logger.info(f"Extracting text from: {file_path}")
        
        if self.use_pdfplumber:
            return self._extract_with_pdfplumber(file_path)
        else:
            return self._extract_with_pypdf2(file_path)
    
    def extract_from_bytes(self, pdf_bytes: bytes) -> ExtractedText:
        """
        Extract text from PDF bytes
        
        Args:
            pdf_bytes: PDF file as bytes
            
        Returns:
            ExtractedText object
        """
        logger.info("Extracting text from PDF bytes")
        
        if self.use_pdfplumber:
            return self._extract_with_pdfplumber_bytes(pdf_bytes)
        else:
            return self._extract_with_pypdf2_bytes(pdf_bytes)
    
    def _extract_with_pdfplumber(self, file_path: str) -> ExtractedText:
        """Extract text using pdfplumber (more accurate)"""
        try:
            with pdfplumber.open(file_path) as pdf:
                return self._process_pdfplumber(pdf, file_path)
        except Exception as e:
            logger.error(f"PDFPlumber extraction failed: {e}")
            # Fallback to PyPDF2
            return self._extract_with_pypdf2(file_path)
    
    def _extract_with_pdfplumber_bytes(self, pdf_bytes: bytes) -> ExtractedText:
        """Extract text from bytes using pdfplumber"""
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                return self._process_pdfplumber(pdf, "bytes_input")
        except Exception as e:
            logger.error(f"PDFPlumber bytes extraction failed: {e}")
            return self._extract_with_pypdf2_bytes(pdf_bytes)
    
    def _process_pdfplumber(self, pdf, source_name: str) -> ExtractedText:
        """Process PDF extracted with pdfplumber"""
        pages = []
        raw_text = ""
        
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text() or ""
            
            # Clean page text
            cleaned_page = self._clean_page_text(page_text, page_num=i+1)
            pages.append(cleaned_page)
            raw_text += page_text + "\n\n"
        
        # Combine all pages
        full_text = "\n".join(pages)
        
        # Get metadata
        metadata = self._extract_metadata(pdf.metadata, source_name, len(pages))
        
        # Segment by speakers
        speaker_segments = self._segment_by_speakers(full_text)
        
        # Final cleaning
        cleaned_text = self._clean_full_text(full_text)
        
        return ExtractedText(
            raw_text=raw_text.strip(),
            cleaned_text=cleaned_text,
            pages=pages,
            page_count=len(pages),
            metadata=metadata,
            speaker_segments=speaker_segments
        )
    
    def _extract_with_pypdf2(self, file_path: str) -> ExtractedText:
        """Extract text using PyPDF2 (fallback method)"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                return self._process_pypdf2(pdf_reader, file_path)
        except Exception as e:
            logger.error(f"PyPDF2 extraction failed: {e}")
            raise
    
    def _extract_with_pypdf2_bytes(self, pdf_bytes: bytes) -> ExtractedText:
        """Extract text from bytes using PyPDF2"""
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            return self._process_pypdf2(pdf_reader, "bytes_input")
        except Exception as e:
            logger.error(f"PyPDF2 bytes extraction failed: {e}")
            raise
    
    def _process_pypdf2(self, pdf_reader, source_name: str) -> ExtractedText:
        """Process PDF extracted with PyPDF2"""
        pages = []
        raw_text = ""
        
        for i, page in enumerate(pdf_reader.pages):
            page_text = page.extract_text() or ""
            
            # Clean page text
            cleaned_page = self._clean_page_text(page_text, page_num=i+1)
            pages.append(cleaned_page)
            raw_text += page_text + "\n\n"
        
        # Combine all pages
        full_text = "\n".join(pages)
        
        # Get metadata
        metadata = self._extract_metadata(pdf_reader.metadata, source_name, len(pdf_reader.pages))
        
        # Segment by speakers
        speaker_segments = self._segment_by_speakers(full_text)
        
        # Final cleaning
        cleaned_text = self._clean_full_text(full_text)
        
        return ExtractedText(
            raw_text=raw_text.strip(),
            cleaned_text=cleaned_text,
            pages=pages,
            page_count=len(pages),
            metadata=metadata,
            speaker_segments=speaker_segments
        )
    
    def _clean_page_text(self, page_text: str, page_num: int) -> str:
        """
        Clean individual page text
        
        Args:
            page_text: Raw text from page
            page_num: Page number
            
        Returns:
            Cleaned page text
        """
        if not page_text:
            return ""
        
        lines = page_text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Skip header patterns
            if any(re.match(pattern, line, re.IGNORECASE) for pattern in self.header_patterns):
                continue
            
            # Skip page numbers
            if any(re.match(pattern, line) for pattern in self.page_num_patterns):
                continue
            
            # Remove excessive whitespace
            line = re.sub(r'\s+', ' ', line)
            
            cleaned_lines.append(line)
        
        # Rejoin lines
        cleaned_page = '\n'.join(cleaned_lines)
        
        # Remove page break markers
        cleaned_page = re.sub(r'-+\s*Page\s+Break\s+-+', '', cleaned_page, flags=re.IGNORECASE)
        
        return cleaned_page
    
    def _clean_full_text(self, text: str) -> str:
        """
        Apply final cleaning to the full document text
        
        Args:
            text: Combined text from all pages
            
        Returns:
            Fully cleaned text
        """
        if not text:
            return ""
        
        # Remove multiple newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Fix hyphenated words across lines
        text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
        
        # Remove extra spaces
        text = re.sub(r'[ \t]{2,}', ' ', text)
        
        # Normalize quotes and dashes
        text = text.replace('"', '"').replace("'", "'")
        text = text.replace('–', '-').replace('—', '-')
        
        # Remove control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t\r')
        
        return text.strip()
    
    def _segment_by_speakers(self, text: str) -> List[Dict[str, Any]]:
        """
        Segment text by speaker turns
        
        Args:
            text: Full document text
            
        Returns:
            List of speaker segments with metadata
        """
        segments = []
        lines = text.split('\n')
        
        current_speaker = None
        current_text = []
        segment_start_line = 0
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Check if line starts with a speaker pattern
            speaker_match = self._extract_speaker_from_line(line)
            
            if speaker_match:
                # Save previous segment if exists
                if current_speaker and current_text:
                    segments.append({
                        'speaker': current_speaker,
                        'text': ' '.join(current_text),
                        'start_line': segment_start_line,
                        'end_line': i-1,
                        'line_count': len(current_text)
                    })
                
                # Start new segment
                current_speaker = speaker_match['name']
                current_text = [speaker_match['remaining_text']] if speaker_match['remaining_text'] else []
                segment_start_line = i
            else:
                # Continue current segment
                if current_text is not None:
                    current_text.append(line)
        
        # Add the last segment
        if current_speaker and current_text:
            segments.append({
                'speaker': current_speaker,
                'text': ' '.join(current_text),
                'start_line': segment_start_line,
                'end_line': len(lines) - 1,
                'line_count': len(current_text)
            })
        
        return segments
    
    def _extract_speaker_from_line(self, line: str) -> Optional[Dict[str, str]]:
        """
        Extract speaker name from a line
        
        Args:
            line: Text line
            
        Returns:
            Dict with 'name' and 'remaining_text' or None
        """
        for pattern in self.speaker_patterns:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                speaker_name = match.group(1).strip()
                
                # Remove the speaker part from the line
                remaining_text = line[match.end():].strip()
                
                # Clean up the speaker name
                speaker_name = re.sub(r'\s+', ' ', speaker_name)
                speaker_name = speaker_name.strip(' :,-')
                
                return {
                    'name': speaker_name,
                    'remaining_text': remaining_text,
                    'pattern_used': pattern
                }
        
        return None
    
    def _extract_metadata(self, pdf_metadata: Dict, source_name: str, page_count: int) -> Dict[str, Any]:
        """
        Extract metadata from PDF
        
        Args:
            pdf_metadata: PDF metadata dictionary
            source_name: Source file name
            page_count: Number of pages
            
        Returns:
            Metadata dictionary
        """
        metadata = {
            'source': source_name,
            'page_count': page_count,
            'extraction_method': 'pdfplumber' if self.use_pdfplumber else 'pypdf2',
            'extracted_date': None,
            'title': None,
            'author': None,
            'creator': None,
            'producer': None,
        }
        
        # Extract from PDF metadata
        if pdf_metadata:
            metadata.update({
                'title': pdf_metadata.get('/Title'),
                'author': pdf_metadata.get('/Author'),
                'creator': pdf_metadata.get('/Creator'),
                'producer': pdf_metadata.get('/Producer'),
                'creation_date': pdf_metadata.get('/CreationDate'),
                'modification_date': pdf_metadata.get('/ModDate'),
            })
        
        # Parse dates from metadata
        metadata['extracted_date'] = self._parse_pdf_date(
            metadata.get('creation_date') or metadata.get('modification_date')
        )
        
        return metadata
    
    def _parse_pdf_date(self, pdf_date: str) -> Optional[str]:
        """
        Parse PDF date format to ISO format
        
        Args:
            pdf_date: PDF date string (e.g., "D:20230101120000")
            
        Returns:
            ISO date string or None
        """
        if not pdf_date:
            return None
        
        try:
            # PDF date format: D:YYYYMMDDHHMMSS
            if pdf_date.startswith('D:'):
                date_str = pdf_date[2:]
                if len(date_str) >= 8:
                    year = date_str[0:4]
                    month = date_str[4:6]
                    day = date_str[6:8]
                    return f"{year}-{month}-{day}"
        except Exception as e:
            logger.warning(f"Failed to parse PDF date {pdf_date}: {e}")
        
        return None
    
    def extract_tables(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract tables from PDF (for budget tables, etc.)
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            List of extracted tables
        """
        if not self.use_pdfplumber:
            logger.warning("Table extraction requires pdfplumber")
            return []
        
        tables = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_tables = page.extract_tables()
                    
                    for table_num, table in enumerate(page_tables):
                        if table:  # Skip empty tables
                            tables.append({
                                'page': page_num + 1,
                                'table_number': table_num + 1,
                                'rows': len(table),
                                'columns': len(table[0]) if table else 0,
                                'data': table,
                                'bbox': page.bbox if hasattr(page, 'bbox') else None
                            })
        except Exception as e:
            logger.error(f"Table extraction failed: {e}")
        
        return tables
    
    def extract_with_layout(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text with layout preservation
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Dictionary with text organized by layout
        """
        if not self.use_pdfplumber:
            logger.warning("Layout extraction requires pdfplumber")
            return {}
        
        layout_data = {
            'columns': [],
            'headers': [],
            'footnotes': [],
            'main_text': []
        }
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # Extract words with positions
                    words = page.extract_words(
                        extra_attrs=["fontname", "size"]
                    )
                    
                    # Group by vertical position (rough column detection)
                    y_positions = sorted(set(word['top'] for word in words))
                    if len(y_positions) > 1:
                        # Simple column detection based on x-position clustering
                        x_positions = [word['x0'] for word in words]
                        # This is simplified - in practice, you'd use clustering
                        
                    # Identify headers (text at top of page)
                    page_height = page.height
                    for word in words:
                        if word['top'] < page_height * 0.1:  # Top 10%
                            layout_data['headers'].append({
                                'text': word['text'],
                                'page': page_num + 1,
                                'position': (word['x0'], word['top'])
                            })
        except Exception as e:
            logger.error(f"Layout extraction failed: {e}")
        
        return layout_data


# Utility functions
def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """
    Convenience function to extract cleaned text from PDF bytes
    
    Args:
        pdf_bytes: PDF file as bytes
        
    Returns:
        Cleaned text string
    """
    extractor = PDFExtractor(use_pdfplumber=True)
    try:
        result = extractor.extract_from_bytes(pdf_bytes)
        return result.cleaned_text
    except Exception as e:
        logger.error(f"Failed to extract text from bytes: {e}")
        return ""

def extract_text_from_pdf_file(file_path: str) -> str:
    """
    Convenience function to extract cleaned text from PDF file
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        Cleaned text string
    """
    extractor = PDFExtractor(use_pdfplumber=True)
    try:
        result = extractor.extract_from_file(file_path)
        return result.cleaned_text
    except Exception as e:
        logger.error(f"Failed to extract text from {file_path}: {e}")
        return ""

def batch_extract_pdfs(pdf_files: List[str]) -> Dict[str, ExtractedText]:
    """
    Extract text from multiple PDF files
    
    Args:
        pdf_files: List of PDF file paths
        
    Returns:
        Dictionary mapping file paths to ExtractedText objects
    """
    extractor = PDFExtractor(use_pdfplumber=True)
    results = {}
    
    for pdf_file in pdf_files:
        try:
            result = extractor.extract_from_file(pdf_file)
            results[pdf_file] = result
            logger.info(f"Successfully extracted: {pdf_file} ({result.page_count} pages)")
        except Exception as e:
            logger.error(f"Failed to extract {pdf_file}: {e}")
            results[pdf_file] = None
    
    return results


# Example usage
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Example 1: Extract from file
    extractor = PDFExtractor(use_pdfplumber=True)
    
    # Sample file path (replace with actual)
    sample_pdf = "data/uploads/test.pdf"
    print(datetime.now())
    if Path(sample_pdf).exists():
        result = extractor.extract_from_file(sample_pdf)
        
        print(f"Extracted {result.page_count} pages")
        print(f"Speaker segments: {len(result.speaker_segments)}")
        print(f"First 500 chars:\n{result.cleaned_text[:500]}...")
        
        # Print speaker segments
        for i, segment in enumerate(result.speaker_segments[:5]):  # First 5
            print(f"\nSpeaker {i+1}: {segment['speaker']}")
            print(f"Text: {segment['text'][:100]}...")
    
    # Example 2: Using convenience function
    text = extract_text_from_pdf_file(sample_pdf)
    print(f"\nExtracted text length: {len(text)} characters")
    print(datetime.now())