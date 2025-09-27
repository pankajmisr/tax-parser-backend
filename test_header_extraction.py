#!/usr/bin/env python3

import sys
import os
sys.path.append('.')

from parser.generic_1120s_parser import GenericForm1120SParser

def test_header_extraction():
    pdf_path = "BTR - 2021 - NEW GALAXY VENTURE LLC.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"PDF file not found: {pdf_path}")
        return
    
    print("Testing Header Field Extraction for Form 1120-S...")
    print("=" * 60)
    
    parser = GenericForm1120SParser()
    
    # Test header field extraction
    header_data = parser.extract_header_fields(pdf_path)
    
    print("\n" + "=" * 60)
    print("HEADER EXTRACTION RESULTS:")
    print("=" * 60)
    
    print(f"Business Activity Code: {header_data.get('business_activity_code', 'Not found')}")
    print(f"Employer ID (EIN): {header_data.get('employer_id', 'Not found')}")
    print(f"Date Incorporated: {header_data.get('date_incorporated', 'Not found')}")
    
    print("\n" + "=" * 60)
    print("ADDITIONAL ANALYSIS - First 20 lines from Form 1120-S page:")
    print("=" * 60)
    
    # Print first 20 lines to help debug any missing patterns
    for i, (y, line) in enumerate(parser.structured_lines[:20]):
        print(f"Line {i+1:2d} (Y={y:6.1f}): {line}")

if __name__ == "__main__":
    test_header_extraction()