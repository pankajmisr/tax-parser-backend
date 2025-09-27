#!/usr/bin/env python3

import sys
import os
sys.path.append('.')

from parser.generic_1120s_parser import GenericForm1120SParser

def test_net_income_extraction():
    pdf_path = "BTR - 2021 - NEW GALAXY VENTURE LLC.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"PDF file not found: {pdf_path}")
        return
    
    print("Testing Net Income Extraction (Ordinary business income)...")
    print("=" * 60)
    
    parser = GenericForm1120SParser()
    
    # Test net income extraction
    net_income = parser.find_line_21_net_income(pdf_path)
    
    print("\n" + "=" * 60)
    print("NET INCOME EXTRACTION RESULT:")
    print("=" * 60)
    
    print(f"Net Income (Ordinary business income): {net_income}")
    
    print("\n" + "=" * 60)
    print("LOOKING FOR 'ordinary business income' patterns:")
    print("=" * 60)
    
    # Print lines that contain relevant patterns for debugging
    for i, (y, line) in enumerate(parser.structured_lines):
        line_lower = line.lower()
        if 'ordinary business income' in line_lower or ('21' in line and 'ordinary' in line_lower):
            print(f"Line {i+1:2d} (Y={y:6.1f}): {line}")

if __name__ == "__main__":
    test_net_income_extraction()