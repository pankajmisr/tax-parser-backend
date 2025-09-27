# Tax Parser Backend

FastAPI backend for parsing IRS Form 1120S tax documents.

## Features

- **Complete Form 1120S parsing**: Revenue, Net Income, Depreciation, Interest, Amortization
- **K-1 partner extraction**: Names, Tax IDs, and distributions
- **Coordinate-based text extraction**: Preserves PDF structure for accuracy
- **Generic parser**: Works with any Form 1120S document

## Setup

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Run the server**:
```bash
python app.py
```

3. **Test with curl**:
```bash
curl -X POST "http://localhost:8000/parse-1120s" -F "file=@your-tax-return.pdf"
```

## API Endpoints

- `POST /parse-1120s` - Parse Form 1120S and return CSV
- `POST /validate-1120s` - Validate PDF and check extractable fields
- `GET /supported-fields` - List all supported extraction fields
- `GET /health` - Health check

## Architecture

- **FastAPI**: REST API framework
- **pdfplumber**: PDF text extraction with coordinates
- **pandas**: CSV data formatting
- **Multi-page extraction**: Page 1 (main form) + Page 14 (amortization) + K-1 forms (partners)