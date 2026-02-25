"""
PDF Text Extraction with Metadata Extraction
Designed for Indian Parliamentary transcripts
"""

import io
import re
from typing import Union, List, Dict, Any, Optional
import pdfplumber
from PyPDF2 import PdfReader


class PDFExtractor:
    """
    Extract structured metadata and clean text from parliamentary PDFs.
    """

    def extract(self, pdf_input: Union[str, bytes]) -> Dict[str, Any]:

        raw_pages = self._extract_pages(pdf_input)

        # Metadata
        metadata = self._extract_metadata(raw_pages[:3])

        # Clean pages
        cleaned_pages = [self._clean_page_text(p) for p in raw_pages]
        full_text = "\n\n".join(cleaned_pages)
        full_text = self._post_process(full_text)

        # Remove header/footer junk
        full_text = self._remove_front_matter(full_text)
        full_text = self._remove_tail_matter(full_text)
        
        
        # Count global interruptions
        interruption_count = len(
            re.findall(r"Interruptions", full_text, re.IGNORECASE)
        )

        metadata["total_interruptions"] = interruption_count
        
        # Structured segmentation
        segments = self._segment_text(full_text)

        return {
            "metadata": metadata,
            "segments": segments
        }

    # EXTRACTION LAYER
    def _extract_pages(self, pdf_input: Union[str, bytes]) -> List[str]:

        pages = []

        try:
            if isinstance(pdf_input, bytes):
                pdf = pdfplumber.open(io.BytesIO(pdf_input))
            else:
                pdf = pdfplumber.open(pdf_input)

            for page in pdf.pages:
                pages.append(page.extract_text() or "")

            pdf.close()

        except Exception:
            # fallback
            if isinstance(pdf_input, bytes):
                reader = PdfReader(io.BytesIO(pdf_input))
            else:
                reader = PdfReader(pdf_input)

            for page in reader.pages:
                pages.append(page.extract_text() or "")

        return pages

    # METADATA EXTRACTION
    
    def _extract_written_time(self, text: str) -> Optional[str]:

        match = re.search(
            r"met at\s+([A-Za-z]+)\s+of the Clock",
            text,
            re.IGNORECASE
        )

        NUMBER_WORDS = {
            "One": 1,
            "Two": 2,
            "Three": 3,
            "Four": 4,
            "Five": 5,
            "Six": 6,
            "Seven": 7,
            "Eight": 8,
            "Nine": 9,
            "Ten": 10,
            "Eleven": 11,
            "Twelve": 12
        }
        
        if match:
            word = match.group(1).capitalize()
            if word in NUMBER_WORDS:
                hour = NUMBER_WORDS[word]
                return f"{hour:02d}.00 hrs"

        return None
    
    def _segment_text(self, text: str) -> List[Dict[str, Optional[str]]]:
        """
        Segment text into speaker/time/paragraph structured units.
        """

        lines = [l.strip() for l in text.split("\n") if l.strip()]

        segments = []

        current_speaker = None
        current_time = None
        current_paragraph_lines = []

        speaker_pattern = re.compile(
            r"^(SHRI|SHRIMATI|SMT\.|DR\.|HON\. SPEAKER|THE SPEAKER|MINISTER OF|THE PRIME MINISTER)[^:]*:",
            re.IGNORECASE
        )

        def flush_segment():
            nonlocal current_paragraph_lines

            if current_paragraph_lines:
                paragraph_text = " ".join(current_paragraph_lines).strip()

                # Count interruptions in this paragraph
                interruption_matches = re.findall(
                    r"Interruptions",
                    paragraph_text,
                    re.IGNORECASE
                )

                interruption_count = len(interruption_matches)

                # Remove interruption markers from text (optional)
                paragraph_text = re.sub(
                    r"\.*\(?Interruptions\)?",
                    "",
                    paragraph_text,
                    flags=re.IGNORECASE
                ).strip()
                
                # remove [Translation], [English], etc
                paragraph_text = re.sub(r"\[[A-Za-z\s]*\]", "", paragraph_text)

                segments.append({
                    "speaker": current_speaker,
                    "time": current_time,
                    "paragraph": paragraph_text,
                    "interruptions": interruption_count
                })

                current_paragraph_lines = []

        for line in lines:

            # --- Detect numeric time marker ---
            numeric_match = re.match(r"^\d{1,2}\.\d{2}\s*hrs$", line, re.IGNORECASE)

            if numeric_match:
                flush_segment()
                current_time = numeric_match.group(0)
                continue

            # --- Detect written time (session start) ---
            written_time = self._extract_written_time(line)
            if written_time:
                flush_segment()
                current_time = written_time
                current_paragraph_lines.append(line)  # keep original text
                continue

            # --- Detect speaker ---
            if speaker_pattern.match(line):
                flush_segment()

                # Extract only part before colon
                speaker_name = line.split(":")[0].strip()
                current_speaker = speaker_name

                # If speech continues on same line after colon
                remainder = line.split(":", 1)[1].strip()
                if remainder:
                    current_paragraph_lines.append(remainder)

                continue
            
            # Detect bracketed speaker line
            bracket_speaker = re.match(r"\[(.*?) in the Chair\]", line, re.IGNORECASE)
            if bracket_speaker:
                current_speaker = bracket_speaker.group(1).strip()
                continue
            
            # Skip obvious junk lines
            if line.startswith("C O N T E N T S"):
                continue

            if "LOK SABHA SECRETARIAT" in line:
                continue
            
            # --- Otherwise normal content ---
            current_paragraph_lines.append(line)

        # Flush final segment
        flush_segment()

        return segments
    
    def _remove_front_matter(self, text: str) -> str:
        """
        Remove everything before actual debate starts.
        """

        # Debate usually starts with:
        # "The Lok Sabha met at"
        # OR first time marker
        # OR first speaker marker

        start_patterns = [
            r"The Lok Sabha met at",
            r"\[\s*HON\.\s*SPEAKER",
            r"\d{1,2}\.\d{2}\s*hrs"
        ]

        for pattern in start_patterns:
            match = re.search(pattern, text)
            if match:
                return text[match.start():]

        return text
    
    def _remove_tail_matter(self, text: str) -> str:
        """
        Remove internet notice / copyright blocks at end.
        """

        end_patterns = [
            r"INTERNET",
            r"Live telecast begins",
            r"Published under Rules",
            r"©\d{4}",
            r"The Lok Sabha then adjourned",
        ]

        for pattern in end_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return text[:match.start()]

        return text
    
    def _extract_metadata(self, pages: List[str]) -> Dict[str, Any]:

        lines = []
        for page in pages:
            lines.extend([l.strip() for l in page.split("\n") if l.strip()])

        text_block = "\n".join(lines)
        metadata = {}

        # Document Type Detection
        if any("LOK SABHA DEBATES" in l for l in lines):
            metadata["document_type"] = "lok_sabha_debate"

        elif any("ADDRESS BY THE HON’BLE PRESIDENT" in l for l in lines):
            metadata["document_type"] = "president_address"

        elif any("Prime Minister's Office" in l for l in lines):
            metadata["document_type"] = "pib_pm_speech"

        elif any(re.search(r"Budget\s+\d{4}-\d{4}", l) for l in lines):
            metadata["document_type"] = "budget_speech"

        else:
            metadata["document_type"] = "unknown"

        doc_type = metadata["document_type"]

        # Type-specific extraction
        if doc_type == "lok_sabha_debate":
            self._extract_lok_sabha_metadata(lines, metadata)

        elif doc_type == "budget_speech":
            self._extract_budget_metadata(lines, metadata)

        elif doc_type == "president_address":
            self._extract_president_metadata(lines, metadata)

        elif doc_type == "pib_pm_speech":
            self._extract_pib_metadata(lines, metadata)

        return metadata

    def _extract_lok_sabha_metadata(self, lines: List[str], metadata: Dict):

        for line in lines:

            # Series line (single line only)
            if "Series" in line and "Vol." in line and "No." in line:
                metadata["series_info"] = line
                break

        # Gregorian date
        for line in lines:
            match = re.search(
                r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+[A-Za-z]+\s+\d{1,2},?\s+\d{4}",
                line
            )
            if match:
                metadata["sitting_date"] = match.group(0)
                break

        # Indian calendar date
        for line in lines:
            match = re.search(
                r"[A-Za-z]+\s+\d{1,2},?\s+\d{4}\s*\(Saka\)",
                line
            )
            if match:
                metadata["indian_calendar_date"] = match.group(0)
                break

        # Session
        for line in lines:
            if "Session" in line:
                metadata["session"] = line
                break

        metadata["house"] = "Lok Sabha"
        
    def _extract_budget_metadata(self, lines: List[str], metadata: Dict):

        for i, line in enumerate(lines):

            # Budget year
            match = re.search(r"Budget\s+(\d{4}-\d{4})", line)
            if match:
                metadata["budget_year"] = match.group(1)

            # Speech of -> next line is speaker
            if line.startswith("Speech of") and i + 1 < len(lines):
                metadata["speaker"] = lines[i + 1]

            # Minister line
            if line.startswith("Minister of"):
                metadata["designation"] = line

            # Date line
            match = re.search(r"[A-Za-z]+\s+\d{1,2},?\s+\d{4}", line)
            if match:
                metadata["date"] = match.group(0)
        
    def _extract_president_metadata(self, lines: List[str], metadata: Dict):

        metadata["speaker_role"] = "President of India"

        for i, line in enumerate(lines):

            if line.startswith("SMT.") and i < len(lines):
                metadata["speaker"] = line.replace("SMT.", "").strip()

            if line.startswith("New Delhi:"):
                metadata["date"] = line.replace("New Delhi:", "").strip()
                metadata["location"] = "New Delhi"
                
    def _extract_pib_metadata(self, lines: List[str], metadata: Dict):

        metadata["source"] = "Press Information Bureau"

        for line in lines:

            if "Prime Minister's Office" in line:
                metadata["issuing_body"] = line

            match = re.search(
                r"Posted On:\s+([0-9]{1,2}\s+[A-Z]{3}\s+\d{4})",
                line
            )
            if match:
                metadata["date"] = match.group(1)
    
    # CLEANING LAYER
    
    def _clean_page_text(self, text: str) -> str:

        lines = text.split("\n")
        cleaned_lines = []

        for line in lines:
            line = line.strip()

            if not line:
                continue

            # Remove page numbers
            if re.match(r"^\d+$", line):
                continue

            if re.match(r"^\d{2}\.\d{2}\.\d{4}\s+\d+$", line):
                continue
            
            # Remove lines that are only special characters (3 or more)
            if re.match(r'^[_\-=.*]{3,}$', line):
                continue

            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    # POST PROCESSING
    
    def _post_process(self, text: str) -> str:
        """
        Normalize spacing and formatting.
        """

        # Remove multiple spaces
        text = re.sub(r"[ \t]+", " ", text)

        # Normalize line breaks
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Remove hyphenated line breaks:
        # e.g., develop-\nment -> development
        text = re.sub(r"-\n(\w+)", r"\1", text)
        
        # Remove inline separators
        text = re.sub(r'\s*[_\-=]{3,}\s*', ' ', text)
        
        # Replace 3+ consecutive special chars with single space
        text = re.sub(r'([_\-=*\.])\1{2,}', ' ', text)
        
        # Remove private-use Unicode glyphs (common in PDFs)
        text = re.sub(r'[\uf000-\uf8ff]', '', text)
        
        # Replace unicode ellipsis with space
        text = text.replace("…", " ")
        
        # Remove standalone symbol tokens
        text = re.sub(r'\s*[\*\u2022\u25CF\u25AA]+\s*', ' ', text)
        
        return text.strip()
    

if __name__ == "__main__":
    extractor = PDFExtractor()
    result = extractor.extract("data/uploads/test.pdf")
    print(result["metadata"])
    print(result["segments"][0])
    print(result["segments"][-1])