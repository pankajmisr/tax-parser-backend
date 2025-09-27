# Tax Parser Backend - CLAUDE.md

## Project Overview
FastAPI backend for parsing IRS Form 1120-S (S Corporation Tax Returns) from PDF documents.

## Project Structure
```
tax-parser-backend/
├── app.py                                    # Main FastAPI application
├── parser/
│   ├── generic_1120s_parser.py             # Main parser for Form 1120-S
│   ├── enhanced_parser.py                  # Enhanced parsing features
│   └── mef_parser.py                       # MEF (Modernized e-File) parser
├── test_*.py                               # Test scripts for validation
├── requirements.txt                        # Python dependencies
├── README.md                              # Project documentation
└── *.pdf                                  # Sample tax documents for testing

```

## Environment Setup
- Virtual environment: `.venv/` (Python virtual environment)
- Dependencies: Install with `pip install -r requirements.txt`

## Key Commands

### Development
```bash
# Activate virtual environment and run server
source .venv/bin/activate && python app.py

# Run tests
python test_page_detection.py
python test_edge_cases.py
python test_btr_document.py
```

### API Testing
```bash
# Test API endpoints
curl -X POST "http://localhost:8000/parse-1120s" -F "file=@document.pdf"
curl -X POST "http://localhost:8000/validate-1120s" -F "file=@document.pdf"
curl -X GET "http://localhost:8000/supported-fields"
curl -X GET "http://localhost:8000/health"
```

## Development Rules & Guidelines

### CRITICAL: No Hardcoded Values
- **NEVER** hardcode specific values from sample documents into the parser code
- **NEVER** use document-specific amounts, names, or identifiers as constants
- All extraction logic must be **generic** and work across different tax documents
- Use **pattern-based extraction** not value-based extraction
- Examples are for testing only, not for hardcoding

### Parser Design Principles
1. **Generic Field Detection**: Use form line numbers, labels, and positioning
2. **Flexible Text Matching**: Use regex patterns, not exact string matches
3. **Multiple Document Support**: Code must work for any valid Form 1120-S
4. **Robust Number Parsing**: Handle various number formats (commas, decimals, negatives)
5. **Error Handling**: Gracefully handle missing or malformed data

## Current Issues to Fix
1. **Revenue Extraction**: Currently showing $0 instead of actual values like $1,881,314
2. **Net Income Scale**: Showing $673 instead of $89,673 (scale factor issue)
3. **Page Detection**: Working correctly but extraction algorithms need refinement

## API Endpoints
- `POST /parse-1120s` - Parse Form 1120-S and return JSON
- `POST /validate-1120s` - Validate and check extractable fields  
- `GET /supported-fields` - List all supported fields
- `GET /health` - Service health check

## Supported Form Fields
- Revenue (Line 1a/1c)
- Net Income (Line 21) 
- Depreciation (Line 14)
- Interest (Line 13)
- Amortization (Various lines)
- Partner/Shareholder information

## Testing Documents
- `2021 Tax Return Documents (POOLVILLE INVESTMENT L) (2).pdf` - Valid 1120-S (working)
- `BTR - 2021 - NEW GALAXY VENTURE LLC.pdf` - Valid 1120-S (extraction issues)
- `BTR - 2021 - NEW KR HOLDING LLC.pdf` - Contains Form 1065 (Partnership, not 1120-S)