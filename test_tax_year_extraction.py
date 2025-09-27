#!/usr/bin/env python3

import sys
import os
sys.path.append('.')

from parser.generic_1120s_parser import GenericForm1120SParser

def test_tax_year_extraction():
    pdf_path = "BTR - 2021 - NEW GALAXY VENTURE LLC.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"PDF file not found: {pdf_path}")
        return
    
    print("Testing Tax Year Extraction...")
    print("=" * 60)
    
    parser = GenericForm1120SParser()
    
    # Test tax year extraction
    header_data = parser.extract_header_fields(pdf_path)
    
    print("\n" + "=" * 60)
    print("TAX YEAR EXTRACTION RESULT:")
    print("=" * 60)
    
    print(f"Tax Year: {header_data.get('tax_year', 'Not found')}")
    print(f"Business Activity Code: {header_data.get('business_activity_code', 'Not found')}")
    print(f"Employer ID (EIN): {header_data.get('employer_id', 'Not found')}")
    print(f"Date Incorporated: {header_data.get('date_incorporated', 'Not found')}")
    
    print("\n" + "=" * 60)
    print("LOOKING FOR YEAR PATTERNS IN FIRST 15 LINES:")
    print("=" * 60)
    
    # Print first 15 lines to help debug year extraction
    for i, (y, line) in enumerate(parser.structured_lines[:15]):
        line_lower = line.lower()
        if any(year in line for year in ['2020', '2021', '2022', '2023', '2024']) or 'calendar year' in line_lower or 'tax year' in line_lower:
            print(f"Line {i+1:2d} (Y={y:6.1f}): {line}")

if __name__ == "__main__":
    test_tax_year_extraction()