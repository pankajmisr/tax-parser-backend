"""
P&L Statement Parser with flexible pattern matching
"""
import re
import logging
from typing import Dict, List, Optional, Any
import pdfplumber
from datetime import datetime

logger = logging.getLogger(__name__)

class PLStatementParser:
    def __init__(self):
        """Initialize with configurable pattern lists for flexibility"""
        
        # Revenue patterns - ordered by priority
        self.revenue_patterns = [
            r"Total Income",
            r"Total Revenue",
            r"Gross Revenue",
            r"Total Sales",
            r"Net Sales",
            r"Sales Revenue",
            r"Operating Revenue"
        ]
        
        # Net income patterns
        self.net_income_patterns = [
            r"Net Income",
            r"Net Profit",
            r"Net Earnings",
            r"Bottom Line",
            r"Total Profit",
            r"Profit After Tax",
            r"Net Profit/Loss",
            r"Net Earnings/Loss"
        ]
        
        # Expense patterns
        self.expense_patterns = [
            r"Total Expenses",
            r"Operating Expenses",
            r"Total Operating Expenses",
            r"Total Costs",
            r"Cost of Operations"
        ]
        
        # Depreciation patterns
        self.depreciation_patterns = [
            r"Depreciation",
            r"Depreciation Expense",
            r"Depreciation & Amortization",
            r"D&A"
        ]
        
        # Interest patterns
        self.interest_patterns = [
            r"Interest Expense",
            r"Interest",
            r"Finance Costs",
            r"Interest Paid"
        ]
        
        # Amortization patterns
        self.amortization_patterns = [
            r"Amortization",
            r"Amortization Expense"
        ]
        
        # Year patterns for extracting from document
        self.year_patterns = [
            r"Year Ended.*?(\d{4})",
            r"For the Year.*?(\d{4})",
            r"Period Ending.*?(\d{4})",
            r"Statement Date.*?(\d{4})",
            r"As of.*?(\d{4})",
            r"(\d{4})\s+P&L",
            r"P&L.*?(\d{4})"
        ]

    def parse(self, pdf_path: str) -> Dict[str, Any]:
        """Main parsing function"""
        try:
            logger.info(f"Starting P&L parsing for: {pdf_path}")
            
            with pdfplumber.open(pdf_path) as pdf:
                # Extract all text from the document
                all_text = ""
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    all_text += page_text + "\n"
                
                # Parse the extracted text
                result = {
                    "document_type": "P&L Statement",
                    "header": self._extract_header(all_text, pdf_path),
                    "revenue": self._extract_value_by_patterns(all_text, self.revenue_patterns),
                    "net_income": self._extract_value_by_patterns(all_text, self.net_income_patterns),
                    "total_expenses": self._extract_value_by_patterns(all_text, self.expense_patterns),
                    "depreciation": self._extract_value_by_patterns(all_text, self.depreciation_patterns),
                    "interest": self._extract_value_by_patterns(all_text, self.interest_patterns),
                    "amortization": self._extract_value_by_patterns(all_text, self.amortization_patterns),
                    "raw_text": all_text[:5000]  # Store first 5000 chars for debugging
                }
                
                logger.info(f"Successfully parsed P&L: {result}")
                return result
                
        except Exception as e:
            logger.error(f"Error parsing P&L statement: {str(e)}")
            raise

    def _extract_header(self, text: str, pdf_path: str) -> Dict[str, Optional[str]]:
        """Extract header information from P&L"""
        header = {}
        
        # Try to extract tax year from document text
        tax_year = self._extract_year_from_text(text)
        
        # If not found in text, try filename
        if not tax_year:
            tax_year = self._extract_year_from_filename(pdf_path)
        
        header["tax_year"] = tax_year
        
        # Try to extract company name (usually at the top)
        lines = text.split('\n')[:10]  # Check first 10 lines
        for line in lines:
            # Skip empty lines and common headers
            if line and not any(skip in line.lower() for skip in ['profit', 'loss', 'statement', 'p&l']):
                # This might be the company name
                if len(line) > 3 and not re.match(r'^\d', line):
                    header["company_name"] = line.strip()
                    break
        
        return header

    def _extract_value_by_patterns(self, text: str, patterns: List[str]) -> Optional[float]:
        """Try multiple patterns to extract a value"""
        for pattern in patterns:
            # Try different regex variations
            regex_patterns = [
                f"{pattern}[:\\s]*\\$?([\\d,]+\\.?\\d*)",  # Pattern: $1,234.56
                f"{pattern}.*?[\\s\\$]+([\\d,]+\\.?\\d*)",  # Pattern with space
                f"{pattern}.*?([\\(\\d,]+\\.?\\d*\\)?)",    # Pattern with parentheses for negatives
            ]
            
            for regex in regex_patterns:
                match = re.search(regex, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    value_str = match.group(1)
                    return self._parse_currency(value_str)
        
        return None

    def _extract_year_from_text(self, text: str) -> Optional[str]:
        """Extract year from document text"""
        for pattern in self.year_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                year = match.group(1)
                # Validate year is reasonable (2000-2030)
                if 2000 <= int(year) <= 2030:
                    return year
        return None

    def _extract_year_from_filename(self, filename: str) -> Optional[str]:
        """Extract year from filename"""
        # Look for 4-digit year in filename
        match = re.search(r'(\d{4})', filename)
        if match:
            year = match.group(1)
            if 2000 <= int(year) <= 2030:
                return year
        return None

    def _parse_currency(self, value_str: str) -> float:
        """Parse currency string to float"""
        if not value_str:
            return 0.0
        
        # Remove currency symbols and whitespace
        value_str = value_str.strip().replace('$', '').replace(',', '')
        
        # Handle negative values in parentheses
        if '(' in value_str and ')' in value_str:
            value_str = '-' + value_str.replace('(', '').replace(')', '')
        
        try:
            return float(value_str)
        except ValueError:
            logger.warning(f"Could not parse currency value: {value_str}")
            return 0.0

    def add_revenue_pattern(self, pattern: str):
        """Add a new revenue pattern for flexibility"""
        if pattern not in self.revenue_patterns:
            self.revenue_patterns.append(pattern)

    def add_expense_pattern(self, pattern: str):
        """Add a new expense pattern for flexibility"""
        if pattern not in self.expense_patterns:
            self.expense_patterns.append(pattern)

    def add_net_income_pattern(self, pattern: str):
        """Add a new net income pattern for flexibility"""
        if pattern not in self.net_income_patterns:
            self.net_income_patterns.append(pattern)