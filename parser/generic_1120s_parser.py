import pdfplumber
import pandas as pd
import re

class GenericForm1120SParser:
    def __init__(self):
        self.structured_lines = []
        self.text_by_page = {}
        self.form_1120s_page = None  # Store the detected Form 1120-S page number
        
    def detect_form_1120s_page(self, pdf_path: str):
        """
        Detect which page contains the Form 1120-S starting page by looking for key indicators.
        Returns the page number (0-indexed) or None if not found.
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_text = page.extract_text() or ""
                    page_text_upper = page_text.upper()
                    
                    # Look for strong indicators that this is the Form 1120-S page
                    indicators = [
                        "1120-S U.S. INCOME TAX RETURN FOR AN S CORPORATION",
                        "FORM 1120-S",
                        "1120S",
                        "S CORPORATION",
                        "GROSS RECEIPTS OR SALES",
                        "ORDINARY BUSINESS INCOME"
                    ]
                    
                    # Must have multiple indicators to be confident
                    matches = sum(1 for indicator in indicators if indicator in page_text_upper)
                    
                    # Also check for specific form structure elements
                    form_structure_indicators = [
                        "LINE 1A",
                        "LINE 21", 
                        "COMPENSATION OF OFFICERS",
                        "SALARIES AND WAGES"
                    ]
                    
                    structure_matches = sum(1 for indicator in form_structure_indicators if indicator in page_text_upper)
                    
                    # If we find strong evidence (multiple matches), this is likely the form page
                    if matches >= 2 or (matches >= 1 and structure_matches >= 2):
                        print(f"Detected Form 1120-S on page {page_num + 1} (0-indexed: {page_num})")
                        print(f"Matches found: {matches}, Structure matches: {structure_matches}")
                        self.form_1120s_page = page_num
                        return page_num
                        
                print("Warning: Could not definitively identify Form 1120-S page, defaulting to page 0")
                self.form_1120s_page = 0
                return 0
                
        except Exception as e:
            print(f"Error detecting Form 1120-S page: {e}")
            self.form_1120s_page = 0
            return 0
        
    def extract_with_coordinates(self, pdf_path: str):
        """Extract text preserving structure using coordinates with improved line grouping"""
        
        # First detect which page contains Form 1120-S
        if self.form_1120s_page is None:
            self.detect_form_1120s_page(pdf_path)
        
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[self.form_1120s_page]  # Use detected page
            
            # Extract words with coordinates
            words = page.extract_words()
            
            print(f"Total words extracted: {len(words)}")
            
            # Improved line grouping - use tolerance for y-coordinates
            lines = {}
            y_tolerance = 3  # Allow small vertical variations within same line
            
            for word in words:
                word_y = word['top']
                
                # Find existing line within tolerance
                matched_y = None
                for existing_y in lines.keys():
                    if abs(word_y - existing_y) <= y_tolerance:
                        matched_y = existing_y
                        break
                
                if matched_y is not None:
                    lines[matched_y].append(word)
                else:
                    lines[word_y] = [word]
            
            print(f"Total lines found: {len(lines)}")
            
            # Sort lines by y-coordinate
            sorted_lines = sorted(lines.items())
            
            # Clear previous lines
            self.structured_lines = []
            
            # Build structured lines with improved spacing
            for y, words_on_line in sorted_lines:
                words_on_line.sort(key=lambda w: w['x0'])
                
                # Build line text with better spacing logic
                line_text = ""
                for i, word in enumerate(words_on_line):
                    if i == 0:
                        # Calculate leading spaces based on x position
                        leading_spaces = max(0, int(word['x0'] / 8))  # Adjusted divisor
                        line_text = " " * leading_spaces + word['text']
                    else:
                        prev_word = words_on_line[i-1]
                        gap = word['x0'] - prev_word['x1']
                        
                        # Improved gap handling
                        if gap > 15:  # Large gap - use multiple spaces
                            num_spaces = max(2, int(gap / 6))
                            line_text += " " * num_spaces + word['text']
                        elif gap > 3:  # Medium gap - use fewer spaces
                            line_text += "  " + word['text']
                        else:  # Small gap - use single space
                            line_text += " " + word['text']
                
                self.structured_lines.append((y, line_text))
            
            print(f"Structured lines created: {len(self.structured_lines)}")
            
            # Print more lines for debugging
            if self.structured_lines:
                print("\nFirst 10 lines:")
                for i, (y, line) in enumerate(self.structured_lines[:10]):
                    print(f"  Y={y:6.1f}: {line}")
                    
                # Print lines around where depreciation might be (around Y=399)
                print("\nLines around Y=399 (depreciation area):")
                for y, line in self.structured_lines:
                    if 390 <= y <= 410:
                        print(f"  Y={y:6.1f}: {line}")

    def extract_header_fields(self, pdf_path: str):
        """Extract Form 1120-S header fields for frontend display"""
        
        # First extract with coordinates if not already done
        if not self.structured_lines:
            self.extract_with_coordinates(pdf_path)
        
        print("=" * 60)
        print("Extracting Form 1120-S Header Fields")
        print("=" * 60)
        
        header_data = {}
        
        # Extract Business Activity Code (Section B)
        header_data['business_activity_code'] = self._find_business_activity_code()
        
        # Extract Employer Identification Number (Section D)
        header_data['employer_id'] = self._find_employer_id()
        
        # Extract Date Incorporated (Section E)
        header_data['date_incorporated'] = self._find_date_incorporated()
        
        # Extract Tax Year
        header_data['tax_year'] = self._find_tax_year()
        
        return header_data
    
    def _find_business_activity_code(self):
        """Find Business activity code number from Section B"""
        
        print("\nLooking for Business Activity Code (Section B)...")
        
        for y, line in self.structured_lines:
            line_lower = line.lower()
            
            # Look for patterns indicating business activity code section
            if ('b' in line_lower and 'business activity code' in line_lower) or \
               ('business activity' in line_lower and 'code' in line_lower):
                print(f"Found business activity section at Y={y}: {line}")
                
                # Look for a numeric code (typically 6 digits)
                code_pattern = r'\b(\d{6})\b'
                match = re.search(code_pattern, line)
                
                if match:
                    code = match.group(1)
                    print(f"Extracted business activity code: {code}")
                    return code
                
                # If not found on same line, check next few lines
                current_index = next((i for i, (ly, _) in enumerate(self.structured_lines) if ly == y), -1)
                if current_index >= 0:
                    for i in range(current_index + 1, min(current_index + 5, len(self.structured_lines))):
                        next_y, next_line = self.structured_lines[i]
                        print(f"Checking line Y={next_y}: {next_line}")
                        match = re.search(code_pattern, next_line)
                        if match:
                            code = match.group(1)
                            print(f"Found business activity code on next line Y={next_y}: {code}")
                            return code
                break
        
        return None
    
    def _find_employer_id(self):
        """Find Employer identification number from Section D"""
        
        print("\nLooking for Employer Identification Number (Section D)...")
        
        for y, line in self.structured_lines:
            line_lower = line.lower()
            
            # Look for patterns indicating employer ID section
            if ('d' in line_lower and 'employer identification' in line_lower) or \
               ('employer id' in line_lower) or ('ein' in line_lower):
                print(f"Found employer ID section at Y={y}: {line}")
                
                # Look for EIN pattern (XX-XXXXXXX)
                ein_pattern = r'\b(\d{2}-\d{7})\b'
                match = re.search(ein_pattern, line)
                
                if match:
                    ein = match.group(1)
                    print(f"Extracted EIN: {ein}")
                    return ein
                
                # If not found on same line, check next few lines
                current_index = next((i for i, (ly, _) in enumerate(self.structured_lines) if ly == y), -1)
                if current_index >= 0:
                    for i in range(current_index + 1, min(current_index + 3, len(self.structured_lines))):
                        next_y, next_line = self.structured_lines[i]
                        match = re.search(ein_pattern, next_line)
                        if match:
                            ein = match.group(1)
                            print(f"Found EIN on next line Y={next_y}: {ein}")
                            return ein
                break
        
        return None
    
    def _find_date_incorporated(self):
        """Find Date incorporated from Section E"""
        
        print("\nLooking for Date Incorporated (Section E)...")
        
        for y, line in self.structured_lines:
            line_lower = line.lower()
            
            # Look for patterns indicating date incorporated section
            if ('e' in line_lower and 'date incorporated' in line_lower) or \
               ('date incorporated' in line_lower):
                print(f"Found date incorporated section at Y={y}: {line}")
                
                # Look for date patterns (MM/DD/YYYY or MM/DD/YY)
                date_patterns = [
                    r'\b(\d{1,2}/\d{1,2}/\d{4})\b',  # MM/DD/YYYY
                    r'\b(\d{1,2}/\d{1,2}/\d{2})\b',  # MM/DD/YY
                    r'\b(\d{1,2} /\d{1,2} /\d{4})\b',  # MM /DD /YYYY (space around slashes)
                    r'\b(\d{1,2} \d{1,2} \d{4})\b',  # MM DD YYYY (space separated)
                ]
                
                for pattern in date_patterns:
                    match = re.search(pattern, line)
                    if match:
                        date = match.group(1)
                        print(f"Extracted date incorporated: {date}")
                        return date
                
                # If not found on same line, check next few lines
                current_index = next((i for i, (ly, _) in enumerate(self.structured_lines) if ly == y), -1)
                if current_index >= 0:
                    for i in range(current_index + 1, min(current_index + 3, len(self.structured_lines))):
                        next_y, next_line = self.structured_lines[i]
                        for pattern in date_patterns:
                            match = re.search(pattern, next_line)
                            if match:
                                date = match.group(1)
                                print(f"Found date incorporated on next line Y={next_y}: {date}")
                                return date
                break
        
        return None
    
    def _find_tax_year(self):
        """Extract tax year from Form 1120-S"""
        
        print("\nLooking for Tax Year...")
        
        for y, line in self.structured_lines:
            line_lower = line.lower()
            
            # Pattern 1: Look for "For calendar year YYYY or tax year beginning" - HIGHEST PRIORITY
            # This is the most specific and reliable pattern on Form 1120-S
            calendar_or_tax_pattern = r'for calendar year (\d{4})\s*or tax year beginning'
            match = re.search(calendar_or_tax_pattern, line_lower)
            if match:
                year = match.group(1)
                print(f"Found tax year from 'calendar year YYYY or tax year beginning' pattern at Y={y}: {year}")
                return year
            
            # Pattern 2: Look for "For calendar year YYYY" pattern (fallback)
            calendar_year_pattern = r'for calendar year (\d{4})'
            match = re.search(calendar_year_pattern, line_lower)
            if match:
                year = match.group(1)
                print(f"Found tax year from calendar year pattern at Y={y}: {year}")
                return year
            
            # Pattern 3: Look for "tax year beginning" pattern with year (fallback)
            tax_year_pattern = r'tax year beginning[^,]*(\d{4})'
            match = re.search(tax_year_pattern, line_lower)
            if match:
                year = match.group(1)
                print(f"Found tax year from tax year beginning pattern at Y={y}: {year}")
                return year
            
            # Pattern 4: Look for standalone 4-digit year in early lines (last resort)
            # Only use this pattern if we're in the first 15 lines AND
            # the line doesn't contain keywords that suggest it's not the tax year
            if len([l for l_y, l in self.structured_lines if l_y <= y]) <= 15:
                # Skip lines that contain procedural references or other non-tax-year contexts
                if any(keyword in line_lower for keyword in ['rev. proc.', 'pursuant to', 'filed', 'election']):
                    continue
                    
                year_pattern = r'\b(20\d{2})\b'
                match = re.search(year_pattern, line)
                if match:
                    year = match.group(1)
                    # Validate it's a reasonable tax year (2010-2030)
                    if 2010 <= int(year) <= 2030:
                        print(f"Found tax year from standalone year pattern at Y={y}: {year}")
                        return year
        
        return None

    def find_line_1a(self, pdf_path: str):
        """Find and extract Line 1a - Gross receipts or sales"""
        
        # First extract with coordinates
        self.extract_with_coordinates(pdf_path)
        
        print("=" * 60)
        print("Finding Line 1a - Gross receipts or sales")
        print("=" * 60)
        
        # Look for line containing both "1a" and "Gross receipts"
        for y, line in self.structured_lines:
            line_lower = line.lower()
            
            # Check if this line has what we're looking for
            if '1a' in line_lower and 'gross receipts' in line_lower:
                print(f"\nFound Line 1a at Y={y}:")
                print(f"Full line: {line}")
                
                # Extract the value - look for numbers with or without commas
                import re
                # Try multiple patterns for flexibility
                value_patterns = [
                    r'1a\s+(\d{1,3}(?:,\d{3})+)',  # Pattern: 1a followed by number with commas
                    r'1a\s+(\d{4,})',              # Pattern: 1a followed by number without commas (4+ digits)
                    r'(\d{1,3}(?:,\d{3})+)',       # Any number with commas
                    r'(\d{6,})'                    # Any large number (6+ digits) without commas
                ]
                
                for pattern in value_patterns:
                    match = re.search(pattern, line)
                    if match:
                        value = match.group(1)
                        print(f"Extracted value using pattern '{pattern}': {value}")
                        return value
                
                print(f"No value pattern matched in line: {line}")
                break
        
        return None
    def find_line_21_net_income(self, pdf_path: str):
        """Find and extract Line 21 - Ordinary business income (loss)"""
        
        # First extract with coordinates if not already done
        if not self.structured_lines:
            self.extract_with_coordinates(pdf_path)
        
        print("=" * 60)
        print("Finding Line 21 - Net Income (Ordinary business income)")
        print("=" * 60)
        
        for y, line in self.structured_lines:
            line_lower = line.lower()
            
            if '21' in line and 'ordinary business income' in line_lower:
                print(f"\nFound Line 21 at Y={y}:")
                print(f"Full line: {line}")
                
                # Check if this is a loss (based on parentheses around the number, not field label)
                has_loss_indicator = False
                
                # Look for value in parentheses (negative) or regular number
                # Try multiple patterns for flexibility
                value_patterns = [
                    r'21\s+(\d{1,3}(?:,\d{3})+)',  # Pattern: 21 followed by number with commas
                    r'21\s+(\d{4,})',              # Pattern: 21 followed by number without commas (4+ digits)
                    r'(\d{1,3}(?:,\d{3})+)\s*$',   # Any number with commas at end
                    r'(\d{5,})\s*$'                # Any large number (5+ digits) at end
                ]
                
                # Check for parentheses first (indicates explicit loss)
                paren_pattern = r'\((\d{1,3}(?:,\d{3})*|\d{4,})\)'
                paren_match = re.search(paren_pattern, line)
                
                if paren_match:
                    value = f"-{paren_match.group(1)}"
                    print(f"Extracted value (in parentheses - loss): {value}")
                    return value
                
                # If no parentheses, try other patterns
                for pattern in value_patterns:
                    match = re.search(pattern, line)
                    if match:
                        value = match.group(1)
                        print(f"Extracted value using pattern '{pattern}': {value}")
                        return value
                
                print(f"No value pattern matched in line: {line}")
                break
        
        return None
    
    def find_line_14_depreciation(self, pdf_path: str):
        """Find and extract Line 14 - Depreciation"""
        
        # First extract with coordinates if not already done
        if not self.structured_lines:
            self.extract_with_coordinates(pdf_path)
        
        print("=" * 60)
        print("Finding Line 14 - Depreciation")
        print("=" * 60)
        
        for y, line in self.structured_lines:
            line_lower = line.lower()
            
            # Look for line containing "14" and "depreciation"
            # The value should now be on the same line after improved extraction
            if '14' in line and 'depreciation' in line_lower:
                print(f"\nFound Line 14 at Y={y}:")
                print(f"Full line: {line}")
                
                # Extract the value from this line
                # Look for a number that's not just "14" or "1125"
                value_pattern = r'(\d{2,}(?:,\d{3})*)'  # At least 2 digits to avoid matching just "14"
                matches = re.findall(value_pattern, line)
                
                for match in matches:
                    # Skip if it's just the line number or form number
                    if match not in ['14', '1125', '4562']:
                        print(f"Extracted value: {match}")
                        return match
                break
        
        return None
    
    def find_line_13_interest(self, pdf_path: str):
        """Find and extract Line 13 - Interest expense"""
        
        # First extract with coordinates if not already done
        if not self.structured_lines:
            self.extract_with_coordinates(pdf_path)
        
        print("=" * 60)
        print("Finding Line 13 - Interest expense")
        print("=" * 60)
        
        for y, line in self.structured_lines:
            line_lower = line.lower()
            
            # Look for line containing "13" and "interest"
            if '13' in line and 'interest' in line_lower:
                print(f"\nFound Line 13 at Y={y}:")
                print(f"Full line: {line}")
                
                # Extract the value from this line
                # Look for a number that's not just "13"
                value_pattern = r'(\d{2,}(?:,\d{3})*)'  # At least 2 digits to avoid matching just "13"
                matches = re.findall(value_pattern, line)
                
                for match in matches:
                    # Skip if it's just the line number
                    if match not in ['13']:
                        print(f"Extracted value: {match}")
                        return match
                break
        
        return None
    
    def extract_page_14_with_coordinates(self, pdf_path: str):
        """Extract Page 14 text preserving structure using coordinates"""
        
        with pdfplumber.open(pdf_path) as pdf:
            # Check if we have at least 14 pages
            if len(pdf.pages) < 14:
                print("PDF has less than 14 pages, cannot extract from Page 14")
                return []
            
            page = pdf.pages[13]  # Page 14
            
            # Extract words with coordinates
            words = page.extract_words()
            
            print(f"Total words extracted from Page 14: {len(words)}")
            
            # Improved line grouping - use tolerance for y-coordinates
            lines = {}
            y_tolerance = 3  # Allow small vertical variations within same line
            
            for word in words:
                word_y = word['top']
                
                # Find existing line within tolerance
                matched_y = None
                for existing_y in lines.keys():
                    if abs(word_y - existing_y) <= y_tolerance:
                        matched_y = existing_y
                        break
                
                if matched_y is not None:
                    lines[matched_y].append(word)
                else:
                    lines[word_y] = [word]
            
            print(f"Total lines found on Page 14: {len(lines)}")
            
            # Sort lines by y-coordinate
            sorted_lines = sorted(lines.items())
            
            # Build structured lines with improved spacing
            structured_lines = []
            for y, words_on_line in sorted_lines:
                words_on_line.sort(key=lambda w: w['x0'])
                
                # Build line text with better spacing logic
                line_text = ""
                for i, word in enumerate(words_on_line):
                    if i == 0:
                        # Calculate leading spaces based on x position
                        leading_spaces = max(0, int(word['x0'] / 8))  # Adjusted divisor
                        line_text = " " * leading_spaces + word['text']
                    else:
                        prev_word = words_on_line[i-1]
                        gap = word['x0'] - prev_word['x1']
                        
                        # Improved gap handling
                        if gap > 15:  # Large gap - use multiple spaces
                            num_spaces = max(2, int(gap / 6))
                            line_text += " " * num_spaces + word['text']
                        elif gap > 3:  # Medium gap - use fewer spaces
                            line_text += "  " + word['text']
                        else:  # Small gap - use single space
                            line_text += " " + word['text']
                
                structured_lines.append((y, line_text))
            
            print(f"Structured lines created for Page 14: {len(structured_lines)}")
            
            # Print all lines for debugging
            if structured_lines:
                print("\nPage 14 structured lines:")
                for i, (y, line) in enumerate(structured_lines):
                    print(f"  Y={y:6.1f}: {line}")
            
            return structured_lines
    
    def find_amortization(self, pdf_path: str):
        """Find and extract Amortization from Page 14 - Federal Supporting Statements"""
        
        print("=" * 60)
        print("Finding Amortization from Page 14 - Supporting Statements")
        print("=" * 60)
        
        # Extract Page 14 with coordinates
        page_14_lines = self.extract_page_14_with_coordinates(pdf_path)
        
        if not page_14_lines:
            print("No structured lines found on Page 14")
            return None
        
        # Look for lines containing "AMORTIZATION" and extract value
        for y, line in page_14_lines:
            line_upper = line.upper()
            if 'AMORTIZATION' in line_upper:
                print(f"\nFound AMORTIZATION at Y={y}:")
                print(f"Full line: {line}")
                
                # Extract the value from this line
                # Look for a number that's not just small numbers
                value_pattern = r'(\d{2,}(?:,\d{3})*)'  # At least 2 digits
                matches = re.findall(value_pattern, line)
                
                for match in matches:
                    # Convert to int for comparison (remove commas)
                    try:
                        value_int = int(match.replace(',', ''))
                        # Look for significant amounts (>1000) to avoid small reference numbers
                        if value_int > 1000:
                            print(f"Extracted value: {match}")
                            return match
                    except:
                        continue
        
        print("AMORTIZATION not found on Page 14")
        return None
    
    def find_k1_pages(self, pdf_path: str):
        """Find all pages that contain Schedule K-1 forms"""
        
        print("=" * 60)
        print("Step 1: Finding all K-1 form pages")
        print("=" * 60)
        
        k1_pages = []
        
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            print(f"Scanning {total_pages} pages for K-1 forms...")
            
            for page_num, page in enumerate(pdf.pages):
                # Extract simple text to check for K-1 indicators
                text = page.extract_text()
                
                if text:
                    text_upper = text.upper()
                    
                    # Look for K-1 form indicators
                    k1_indicators = [
                        "SCHEDULE K-1",
                        "SHAREHOLDER'S SHARE",
                        "CURRENT YEAR INCOME",
                        "DEDUCTIONS, CREDITS, AND OTHER ITEMS"
                    ]
                    
                    # Check if this page contains K-1 indicators
                    found_indicators = []
                    for indicator in k1_indicators:
                        if indicator in text_upper:
                            found_indicators.append(indicator)
                    
                    # If we found multiple K-1 indicators, this is likely a K-1 page
                    if len(found_indicators) >= 2:
                        k1_pages.append(page_num + 1)  # Convert to 1-based page numbering
                        print(f"  ✓ Found K-1 on Page {page_num + 1}")
                        print(f"    Indicators found: {found_indicators}")
                    
                    # Also check for specific K-1 OMB number
                    if "1545-0123" in text and "K-1" in text_upper:
                        if (page_num + 1) not in k1_pages:
                            k1_pages.append(page_num + 1)
                            print(f"  ✓ Found K-1 on Page {page_num + 1} (OMB number)")
        
        print(f"\nTotal K-1 pages found: {len(k1_pages)}")
        print(f"K-1 pages: {k1_pages}")
        
        return k1_pages
    
    def extract_k1_page_with_coordinates(self, pdf_path: str, page_number: int):
        """Extract specific K-1 page text preserving structure using coordinates"""
        
        print(f"\nStep 2: Extracting K-1 Page {page_number} with coordinates")
        print("-" * 50)
        
        with pdfplumber.open(pdf_path) as pdf:
            # Check if page exists
            if page_number > len(pdf.pages) or page_number < 1:
                print(f"Page {page_number} does not exist")
                return []
            
            page = pdf.pages[page_number - 1]  # Convert to 0-based index
            
            # Extract words with coordinates
            words = page.extract_words()
            
            print(f"Total words extracted from K-1 Page {page_number}: {len(words)}")
            
            # Improved line grouping - use tolerance for y-coordinates
            lines = {}
            y_tolerance = 3  # Allow small vertical variations within same line
            
            for word in words:
                word_y = word['top']
                
                # Find existing line within tolerance
                matched_y = None
                for existing_y in lines.keys():
                    if abs(word_y - existing_y) <= y_tolerance:
                        matched_y = existing_y
                        break
                
                if matched_y is not None:
                    lines[matched_y].append(word)
                else:
                    lines[word_y] = [word]
            
            print(f"Total lines found on K-1 Page {page_number}: {len(lines)}")
            
            # Sort lines by y-coordinate
            sorted_lines = sorted(lines.items())
            
            # Build structured lines with improved spacing
            structured_lines = []
            for y, words_on_line in sorted_lines:
                words_on_line.sort(key=lambda w: w['x0'])
                
                # Build line text with better spacing logic
                line_text = ""
                for i, word in enumerate(words_on_line):
                    if i == 0:
                        # Calculate leading spaces based on x position
                        leading_spaces = max(0, int(word['x0'] / 8))  # Adjusted divisor
                        line_text = " " * leading_spaces + word['text']
                    else:
                        prev_word = words_on_line[i-1]
                        gap = word['x0'] - prev_word['x1']
                        
                        # Improved gap handling
                        if gap > 15:  # Large gap - use multiple spaces
                            num_spaces = max(2, int(gap / 6))
                            line_text += " " * num_spaces + word['text']
                        elif gap > 3:  # Medium gap - use fewer spaces
                            line_text += "  " + word['text']
                        else:  # Small gap - use single space
                            line_text += " " + word['text']
                
                structured_lines.append((y, line_text))
            
            print(f"Structured lines created for K-1 Page {page_number}: {len(structured_lines)}")
            
            # Print all lines for debugging
            if structured_lines:
                print(f"\nK-1 Page {page_number} structured lines:")
                for i, (y, line) in enumerate(structured_lines):
                    print(f"  Y={y:6.1f}: {line}")
            
            return structured_lines
    
    def parse_partner_from_k1_lines(self, structured_lines, page_number):
        """Extract partner information from K-1 structured lines"""
        
        print(f"\nStep 3: Parsing partner info from K-1 Page {page_number}")
        print("-" * 50)
        
        partner = {
            'name': None,
            'tax_id': None,
            'distribution': None
        }
        
        # Look for partner name - typically in upper area of K-1
        for y, line in structured_lines:
            line_clean = line.strip()
            line_upper = line_clean.upper()
            
            # Skip empty lines and form headers
            if not line_clean or len(line_clean) < 3:
                continue
            
            # Skip obvious form elements
            skip_patterns = [
                'SCHEDULE K-1', 'OMB NO.', 'DEPARTMENT', 'INTERNAL REVENUE',
                'FOR CALENDAR YEAR', 'TAX YEAR', 'BEGINNING', 'ENDING',
                'SHAREHOLDER\'S SHARE', 'CURRENT YEAR INCOME', 'DEDUCTIONS',
                'CORPORATION\'S', 'EMPLOYER IDENTIFICATION'
            ]
            
            should_skip = False
            for skip_pattern in skip_patterns:
                if skip_pattern in line_upper:
                    should_skip = True
                    break
            
            if should_skip:
                continue
            
            # Look for partner name patterns
            # Names are usually all caps and substantial length
            if (len(line_clean) > 5 and 
                line_clean.isupper() and 
                not any(char.isdigit() for char in line_clean) and
                not partner['name']):
                
                # Additional validation - should look like a name
                words = line_clean.split()
                if len(words) >= 2:  # At least 2 words for a name
                    # Check if it looks like a real name/entity
                    name_indicators = [
                        'FAMILY', 'TRUST', 'LLC', 'CORP', 'INC', 'LP', 'LLP',
                        'PARTNERSHIP', 'COMPANY', 'CO'
                    ]
                    
                    # If it contains name indicators or is just words (personal name)
                    if (any(indicator in line_upper for indicator in name_indicators) or 
                        all(word.isalpha() for word in words)):
                        partner['name'] = line_clean
                        print(f"  Found partner name: {partner['name']}")
            
            # Look for Tax ID (SSN/EIN) - patterns like 123-45-6789 or 12-3456789
            tax_id_pattern = r'(\d{2,3}[-\s]\d{2,3}[-\s]\d{3,4})'
            tax_id_match = re.search(tax_id_pattern, line)
            if tax_id_match and not partner['tax_id']:
                partner['tax_id'] = tax_id_match.group(1)
                print(f"  Found tax ID: {partner['tax_id']}")
            
            # Look for distributions (Line 16) - look for "16" and amounts
            if '16' in line and not partner['distribution']:
                # Look for monetary amounts on line with "16"
                amount_pattern = r'(\d{1,3}(?:,\d{3})*)'
                amounts = re.findall(amount_pattern, line)
                
                for amount in amounts:
                    # Skip the line number itself
                    if amount != '16':
                        try:
                            amount_value = int(amount.replace(',', ''))
                            # Look for significant distribution amounts
                            if amount_value > 100:  # Meaningful distribution
                                partner['distribution'] = amount
                                print(f"  Found distribution: {partner['distribution']}")
                                break
                        except:
                            continue
        
        print(f"  Partner extraction complete:")
        print(f"    Name: {partner['name']}")
        print(f"    Tax ID: {partner['tax_id']}")
        print(f"    Distribution: {partner['distribution']}")
        
        return partner
    
    def find_partners(self, pdf_path: str):
        """Main method to find all partners from K-1 forms"""
        
        print("=" * 60)
        print("Finding Partners/Shareholders from K-1 Forms")
        print("=" * 60)
        
        # Step 1: Find all K-1 pages
        k1_pages = self.find_k1_pages(pdf_path)
        
        if not k1_pages:
            print("No K-1 pages found")
            return []
        
        partners = []
        
        # Step 2 & 3: Extract and parse each K-1 page
        for page_num in k1_pages:
            # Step 2: Extract with coordinates
            structured_lines = self.extract_k1_page_with_coordinates(pdf_path, page_num)
            
            if structured_lines:
                # Step 3: Parse partner info
                partner = self.parse_partner_from_k1_lines(structured_lines, page_num)
                
                # Only add if we found meaningful partner info
                if partner['name'] or partner['tax_id']:
                    partners.append(partner)
        
        print(f"\n" + "=" * 60)
        print(f"Total partners found: {len(partners)}")
        for i, partner in enumerate(partners):
            print(f"Partner {i+1}: {partner['name']} | Tax ID: {partner['tax_id']} | Distribution: {partner['distribution']}")
        
        return partners
    
    def _extract_all_pages(self, pdf_path: str):
        """Extract text from all pages of the PDF"""
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                self.text_by_page[page_num] = text or ""
    
    def parse_tax_return(self, pdf_path: str):
        """Parse the complete tax return and return as DataFrame"""
        try:
            # Extract all required fields
            revenue = self.find_line_1a(pdf_path)
            net_income = self.find_line_21_net_income(pdf_path)
            depreciation = self.find_line_14_depreciation(pdf_path)
            interest = self.find_line_13_interest(pdf_path)
            amortization = self.find_amortization(pdf_path)
            partners = self.find_partners(pdf_path)
            
            # Create DataFrame
            data = [
                {"Field": "Revenue", "Value": revenue or 0},
                {"Field": "Net Income", "Value": net_income or 0},
                {"Field": "Depreciation", "Value": depreciation or 0},
                {"Field": "Interest", "Value": interest or 0},
                {"Field": "Amortization", "Value": amortization or 0}
            ]
            
            # Add partner information
            for i, partner in enumerate(partners):
                partner_num = i + 1
                data.append({"Field": f"Partner {partner_num} Name", "Value": partner.get('name', '')})
                data.append({"Field": f"Partner {partner_num} Tax ID", "Value": partner.get('tax_id', '')})
                data.append({"Field": f"Partner {partner_num} Distribution", "Value": partner.get('distribution', 0)})
            
            return pd.DataFrame(data)
        except Exception:
            return pd.DataFrame([])