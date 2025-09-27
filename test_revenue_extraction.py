#!/usr/bin/env python3

import sys
import os
sys.path.append('.')

from parser.generic_1120s_parser import GenericForm1120SParser

def test_revenue_extraction():
    pdf_path = "BTR - 2021 - NEW GALAXY VENTURE LLC.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"PDF file not found: {pdf_path}")
        return
    
    print("Testing Revenue Extraction (Line 1a - Gross receipts or sales)...")
    print("=" * 60)
    
    parser = GenericForm1120SParser()
    
    # Test revenue extraction
    revenue = parser.find_line_1a(pdf_path)
    
    print("\n" + "=" * 60)
    print("REVENUE EXTRACTION RESULT:")
    print("=" * 60)
    
    print(f"Revenue (Line 1a): {revenue}")
    
    print("\n" + "=" * 60)
    print("LOOKING FOR '1a' AND 'gross receipts' patterns:")
    print("=" * 60)
    
    # Print lines that contain relevant patterns for debugging
    for i, (y, line) in enumerate(parser.structured_lines):
        line_lower = line.lower()
        if '1a' in line_lower or 'gross receipts' in line_lower or 'gross' in line_lower:
            print(f"Line {i+1:2d} (Y={y:6.1f}): {line}")

if __name__ == "__main__":
    test_revenue_extraction()