from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import os
import tempfile
from datetime import datetime
from typing import Optional
import re

# Import the parsers
from parser.generic_1120s_parser import GenericForm1120SParser
from parser.pl_parser import PLStatementParser


app = FastAPI(
    title="Tax Document Parser API",
    description="Parse IRS Form 1120-S (S Corporation Tax Return) and P&L Statements to extract key financial data",
    version="3.0.0"
)

# Add CORS middleware for web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# In your app.py file, update the parse endpoint to use the new parser:

@app.post("/parse-1120s")
async def parse_form_1120s(
    file: UploadFile = File(...)
):
    """Parse Form 1120-S using coordinate-based extraction - returns JSON"""
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_pdf_path = temp_file.name
    
    try:
        # Use the new parser
        parser = GenericForm1120SParser()
        
        # First detect which page contains Form 1120-S
        form_page = parser.detect_form_1120s_page(temp_pdf_path)
        print(f"Form 1120-S detected on page {form_page + 1}")
        
        # Extract with coordinates first
        parser.extract_with_coordinates(temp_pdf_path)
        
        # Extract header fields
        header_data = parser.extract_header_fields(temp_pdf_path)
        
        # Extract individual fields
        revenue = parser.find_line_1a(temp_pdf_path)
        net_income = parser.find_line_21_net_income(temp_pdf_path)
        depreciation = parser.find_line_14_depreciation(temp_pdf_path)
        interest = parser.find_line_13_interest(temp_pdf_path)
        amortization = parser.find_amortization(temp_pdf_path)
        partners = parser.find_partners(temp_pdf_path)
        
        # Convert string values to numbers for JSON response
        def parse_number(value):
            if value is None or value == '':
                return None
            if isinstance(value, str):
                # Remove commas and convert to float
                try:
                    return float(value.replace(',', ''))
                except:
                    return None
            return value
        
        # Return extracted fields as JSON
        result = {
            "header": {
                "business_activity_code": header_data.get('business_activity_code'),
                "employer_id": header_data.get('employer_id'),
                "date_incorporated": header_data.get('date_incorporated'),
                "tax_year": header_data.get('tax_year')
            },
            "revenue": parse_number(revenue),
            "net_income": parse_number(net_income),
            "depreciation": parse_number(depreciation),
            "interest": parse_number(interest),
            "amortization": parse_number(amortization)
        }
        
        return JSONResponse(content={
            "status": "success",
            "data": result
        })
    
    finally:
        if os.path.exists(temp_pdf_path):
            os.unlink(temp_pdf_path)

@app.post("/parse-pl")
async def parse_pl_statement(
    file: UploadFile = File(...)
):
    """Parse P&L Statement using flexible pattern matching - returns JSON"""
    
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_pdf_path = temp_file.name
    
    try:
        # Use P&L parser
        parser = PLStatementParser()
        
        # Parse the P&L statement
        result = parser.parse(temp_pdf_path)
        
        # Ensure numeric values are properly formatted for JSON
        def ensure_numeric(value):
            if value is None or value == '':
                return None
            if isinstance(value, (int, float)):
                return value
            return None
        
        # Format the result for API response
        formatted_result = {
            "header": result.get("header", {}),
            "revenue": ensure_numeric(result.get("revenue")),
            "net_income": ensure_numeric(result.get("net_income")),
            "total_expenses": ensure_numeric(result.get("total_expenses")),
            "depreciation": ensure_numeric(result.get("depreciation")),
            "interest": ensure_numeric(result.get("interest")),
            "amortization": ensure_numeric(result.get("amortization"))
        }
        
        return JSONResponse(content={
            "status": "success",
            "document_type": "P&L Statement",
            "data": formatted_result
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing P&L statement: {str(e)}")
    
    finally:
        if os.path.exists(temp_pdf_path):
            os.unlink(temp_pdf_path)

@app.post("/validate-1120s")
async def validate_form_1120s(file: UploadFile = File(...)):
    """
    Validate that a PDF is a valid Form 1120-S and check what fields can be extracted
    
    Returns detailed information about extractable fields
    """
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_pdf_path = temp_file.name
    
    try:
        parser = GenericForm1120SParser()
        parser._extract_all_pages(temp_pdf_path)
        
        # Check if this appears to be a Form 1120-S
        is_1120s = False
        form_year = None
        
        page1_text = parser.text_by_page.get(0, "")
        
        # Check for Form 1120-S indicators
        if "1120-S" in page1_text or "1120S" in page1_text:
            is_1120s = True
        
        # Try to extract tax year
        year_match = re.search(r'(20\d{2})', page1_text)
        if year_match:
            form_year = year_match.group(1)
        
        # Parse to see what fields we can extract
        df = parser.parse_tax_return(temp_pdf_path)
        
        # Count extracted fields
        fields_found = {}
        for _, row in df.iterrows():
            field = row['Field']
            value = row['Value']
            if value and value != 0 and value != '':
                fields_found[field] = value
        
        return {
            "is_form_1120s": is_1120s,
            "form_year": form_year,
            "filename": file.filename,
            "total_pages": len(parser.text_by_page),
            "fields_extracted": len(fields_found),
            "extracted_fields": fields_found,
            "missing_fields": [
                row['Field'] for _, row in df.iterrows() 
                if not row['Value'] or row['Value'] == 0 or row['Value'] == ''
            ],
            "extraction_quality": "high" if len(fields_found) >= 4 else "medium" if len(fields_found) >= 2 else "low"
        }
    
    finally:
        if os.path.exists(temp_pdf_path):
            os.unlink(temp_pdf_path)


@app.get("/supported-fields")
async def get_supported_fields():
    """
    Get list of fields that this parser can extract from Form 1120-S
    """
    return {
        "form_type": "IRS Form 1120-S",
        "description": "U.S. Income Tax Return for an S Corporation",
        "supported_fields": [
            {
                "field": "Name of business",
                "line": "Header",
                "description": "Legal name of the S Corporation"
            },
            {
                "field": "Revenue",
                "line": "1a/1c",
                "description": "Gross receipts or sales"
            },
            {
                "field": "Net Income",
                "line": "21",
                "description": "Ordinary business income (loss)"
            },
            {
                "field": "Depreciation",
                "line": "14",
                "description": "Depreciation not claimed elsewhere"
            },
            {
                "field": "Interest",
                "line": "13",
                "description": "Interest expense"
            },
            {
                "field": "Amortization",
                "line": "Various",
                "description": "Amortization expenses (from statements or Form 4562)"
            },
            {
                "field": "Partner Names",
                "line": "K-1",
                "description": "Names of shareholders/partners from Schedule K-1"
            },
            {
                "field": "Partner Distributions",
                "line": "K-1 Line 16",
                "description": "Distribution amounts to shareholders/partners"
            }
        ],
        "notes": [
            "PDF must have searchable text (OCR)",
            "Works with any year's Form 1120-S",
            "Handles both positive and negative values",
            "Extracts up to 5 partners/shareholders"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Generic Form 1120-S Parser",
        "version": "2.0.0",
        "supported_forms": ["1120-S"]
    }


@app.get("/")
async def root():
    """API information and usage guide"""
    return {
        "service": "Generic Form 1120-S Parser API",
        "version": "2.0.0",
        "description": "Extract financial data from any IRS Form 1120-S",
        "documentation": "/docs",
        "endpoints": {
            "/parse-1120s": "POST - Parse Form 1120-S and return JSON",
            "/parse-pl": "POST - Parse P&L Statement and return JSON",
            "/validate-1120s": "POST - Validate and check extractable fields",
            "/supported-fields": "GET - List all supported fields",
            "/health": "GET - Service health check"
        },
        "usage_example": {
            "curl": "curl -X POST 'http://localhost:8000/parse-1120s' -F 'file=@form1120s.pdf'",
            "python": "requests.post('http://localhost:8000/parse-1120s', files={'file': open('form1120s.pdf', 'rb')})"
        },
        "features": [
            "Works with any S Corporation's Form 1120-S",
            "Handles various PDF text extraction qualities",
            "Extracts main financial metrics",
            "Includes shareholder/partner information",
            "Returns standardized JSON format"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)