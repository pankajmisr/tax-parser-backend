#!/usr/bin/env python3

import sys
import os
sys.path.append('.')

from parser.generic_1120s_parser import GenericForm1120SParser

def test_btr_document():
    pdf_path = "BTR - 2021 - NEW KR HOLDING LLC.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"PDF file not found: {pdf_path}")
        return
    
    print("Testing BTR document page detection...")
    print("=" * 60)
    
    parser = GenericForm1120SParser()
    
    # Test page detection on this document
    detected_page = parser.detect_form_1120s_page(pdf_path)
    
    print(f"\nResult: Page detection result for BTR document: {detected_page + 1 if detected_page is not None else 'None'}")
    
    # Let's manually check what this document actually contains
    print("\nManual analysis of BTR document pages:")
    print("-" * 40)
    
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages[:10]):  # Check first 10 pages
            page_text = page.extract_text() or ""
            page_text_upper = page_text.upper()
            
            # Check for different form types
            form_indicators = []
            if "1120-S" in page_text_upper:
                form_indicators.append("Form 1120-S")
            if "1065" in page_text_upper and "PARTNERSHIP" in page_text_upper:
                form_indicators.append("Form 1065 (Partnership)")
            if "1040" in page_text_upper:
                form_indicators.append("Form 1040")
            if "COVER LETTER" in page_text_upper or "POST SESSION" in page_text_upper:
                form_indicators.append("Cover/Admin Letter")
                
            print(f"Page {page_num + 1}: {', '.join(form_indicators) if form_indicators else 'No tax forms detected'}")
            
            # Show first few lines to understand content
            lines = page_text.split('\n')[:3]
            for line in lines:
                if line.strip():
                    print(f"  Sample: {line.strip()[:80]}...")
                    break
            print()

if __name__ == "__main__":
    test_btr_document()