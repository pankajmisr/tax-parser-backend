#!/usr/bin/env python3

import sys
import os
sys.path.append('.')

from parser.generic_1120s_parser import GenericForm1120SParser

def test_page_detection():
    pdf_path = "2021 Tax Return Documents (POOLVILLE INVESTMENT L) (2).pdf"
    
    if not os.path.exists(pdf_path):
        print(f"PDF file not found: {pdf_path}")
        return
    
    print("Testing Form 1120-S page detection...")
    print("=" * 50)
    
    parser = GenericForm1120SParser()
    
    # Test page detection
    detected_page = parser.detect_form_1120s_page(pdf_path)
    
    print(f"\nResult: Form 1120-S detected on page {detected_page + 1} (0-indexed: {detected_page})")
    
    # Test extraction from detected page
    print("\nTesting extraction with auto-detected page...")
    parser.extract_with_coordinates(pdf_path)
    
    print(f"\nExtracted {len(parser.structured_lines)} lines from detected page")
    
    # Show first few lines as sample
    print("\nFirst 10 lines extracted:")
    for i, line in enumerate(parser.structured_lines[:10]):
        print(f"{i+1}: {line}")

if __name__ == "__main__":
    test_page_detection()