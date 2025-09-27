import re
import pdfplumber
from typing import Dict, Any, List, Optional
from schemas.mef_field_mappings import FORM_1120S_MEF_MAPPING, MEF_DATA_TYPES, MEF_CALCULATIONS


class MeFCompliantParser:
    """
    High-accuracy tax parser using IRS MeF (Modernized e-File) standards
    Assumes PDFs have OCR text available
    """
    
    def __init__(self):
        self.field_mappings = FORM_1120S_MEF_MAPPING
        self.data_types = MEF_DATA_TYPES
        self.calculations = MEF_CALCULATIONS
        
    def parse_1120s(self, pdf_path: str) -> Dict[str, Any]:
        """
        Parse Form 1120S using MeF-compliant field extraction
        
        Args:
            pdf_path: Path to PDF file (with OCR text)
            
        Returns:
            Dict with MeF field names and validation results
        """
        # Extract all text from PDF
        full_text = self._extract_pdf_text(pdf_path)
        
        # Extract fields using MeF patterns
        extracted_data = {}
        extraction_confidence = {}
        
        for mef_field, config in self.field_mappings.items():
            result = self._extract_field(full_text, mef_field, config)
            extracted_data[mef_field] = result['value']
            extraction_confidence[mef_field] = result['confidence']
        
        
        # Validate extracted data against MeF standards
        validation_results = self._validate_mef_compliance(extracted_data)
        
        # Check calculation consistency
        calculation_results = self._validate_calculations(extracted_data)
        
        return {
            'status': 'success' if validation_results['valid'] else 'validation_failed',
            'data': extracted_data,
            'confidence_scores': extraction_confidence,
            'mef_validation': validation_results,
            'calculation_validation': calculation_results,
            'requires_review': self._needs_manual_review(extraction_confidence, validation_results)
        }
    
    def _extract_pdf_text(self, pdf_path: str) -> str:
        """Extract all text from PDF (assumes OCR is available)"""
        full_text = ""
        
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"
        
        # Keep original text for better pattern matching
        return full_text
    
    def _extract_field(self, text: str, mef_field: str, config: Dict) -> Dict:
        """
        Extract a specific MeF field using multiple pattern matching
        
        Args:
            text: Full PDF text
            mef_field: MeF field name
            config: Field configuration from mapping
            
        Returns:
            Dict with extracted value and confidence score
        """
        patterns = config.get('patterns', [])
        best_match = None
        highest_confidence = 0.0
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                if match.group(1):
                    value = self._clean_extracted_value(match.group(1), config['data_type'])
                    confidence = self._calculate_confidence(match, text, config)
                    
                    if confidence > highest_confidence:
                        best_match = value
                        highest_confidence = confidence
        
        return {
            'value': best_match,
            'confidence': highest_confidence
        }
    
    def _clean_extracted_value(self, raw_value: str, data_type: str) -> Any:
        """Clean and convert extracted value based on MeF data type"""
        
        if data_type == "USAmountType":
            # Remove commas, handle negatives
            cleaned = re.sub(r'[,$\s]', '', raw_value)
            
            # Handle parentheses as negative
            if cleaned.startswith('(') and cleaned.endswith(')'):
                cleaned = '-' + cleaned[1:-1]
            
            try:
                return float(cleaned)
            except ValueError:
                return None
                
        elif data_type in ["EINType", "BusinessActivityCodeType", "BusinessNameType"]:
            return raw_value.strip()
            
        return raw_value
    
    def _calculate_confidence(self, match: re.Match, full_text: str, config: Dict) -> float:
        """
        Calculate confidence score for extracted value
        Based on pattern specificity and context
        """
        base_confidence = 0.5
        
        # Higher confidence for more specific patterns
        pattern_specificity = len(match.group(0)) / len(full_text)
        base_confidence += min(pattern_specificity * 10, 0.3)
        
        # Check for line number context
        if config.get('form_line') and config['form_line'] in match.group(0):
            base_confidence += 0.2
        
        # Check for field description context  
        if config.get('description'):
            desc_words = config['description'].lower().split()
            context = match.group(0).lower()
            matching_words = sum(1 for word in desc_words if word in context)
            base_confidence += (matching_words / len(desc_words)) * 0.2
        
        return min(base_confidence, 1.0)
    
    def _validate_mef_compliance(self, data: Dict[str, Any]) -> Dict:
        """Validate extracted data against MeF data type rules"""
        
        validation_errors = []
        field_validations = {}
        
        for field_name, value in data.items():
            if value is None:
                if self.field_mappings[field_name].get('required', False):
                    validation_errors.append(f"Required field {field_name} is missing")
                    field_validations[field_name] = False
                continue
            
            # Get data type for this field
            data_type = self.field_mappings[field_name]['data_type']
            type_rules = self.data_types.get(data_type, {})
            
            field_valid = True
            
            # Validate based on data type
            if data_type == "USAmountType":
                if not isinstance(value, (int, float)):
                    validation_errors.append(f"{field_name}: Invalid amount format")
                    field_valid = False
                elif value < type_rules.get('min_value', float('-inf')) or value > type_rules.get('max_value', float('inf')):
                    validation_errors.append(f"{field_name}: Amount out of valid range")
                    field_valid = False
                    
            elif data_type == "EINType":
                if not re.match(type_rules['pattern'], str(value)):
                    validation_errors.append(f"{field_name}: Invalid EIN format")
                    field_valid = False
                    
            elif data_type == "BusinessActivityCodeType":
                if not re.match(type_rules['pattern'], str(value)):
                    validation_errors.append(f"{field_name}: Invalid business activity code format")
                    field_valid = False
            
            field_validations[field_name] = field_valid
        
        return {
            'valid': len(validation_errors) == 0,
            'errors': validation_errors,
            'field_validations': field_validations
        }
    
    def _validate_calculations(self, data: Dict[str, Any]) -> Dict:
        """Validate calculated fields against form math"""
        
        calculation_errors = []
        
        for field_name, calc_config in self.calculations.items():
            if field_name not in data or data[field_name] is None:
                continue
                
            formula = calc_config['formula']
            tolerance = calc_config.get('tolerance', 0.01)
            
            # Parse and evaluate formula
            try:
                calculated_value = self._evaluate_formula(formula, data)
                actual_value = data[field_name]
                
                if abs(calculated_value - actual_value) > tolerance:
                    calculation_errors.append(
                        f"{field_name}: Calculation mismatch. "
                        f"Expected {calculated_value}, got {actual_value}"
                    )
                    
            except Exception as e:
                calculation_errors.append(f"{field_name}: Calculation error - {str(e)}")
        
        return {
            'valid': len(calculation_errors) == 0,
            'errors': calculation_errors
        }
    
    def _evaluate_formula(self, formula: str, data: Dict[str, Any]) -> float:
        """Safely evaluate a calculation formula"""
        
        # Replace field names with actual values
        for field_name, value in data.items():
            if value is not None:
                formula = formula.replace(field_name, str(value))
        
        # Basic safety check - only allow numbers, operators, and spaces
        if re.match(r'^[\d\s\+\-\*\/\.\(\)]+$', formula):
            return eval(formula)
        else:
            raise ValueError("Invalid formula contains unsafe characters")
    
    def _needs_manual_review(self, confidence_scores: Dict, validation_results: Dict) -> bool:
        """Determine if extracted data needs manual review"""
        
        # Low confidence threshold
        low_confidence_fields = [
            field for field, score in confidence_scores.items() 
            if score < 0.85
        ]
        
        # Any validation failures
        validation_failures = not validation_results['valid']
        
        # Required fields missing
        required_fields_missing = any(
            self.field_mappings[field].get('required', False) and confidence_scores[field] == 0
            for field in confidence_scores
        )
        
        return bool(low_confidence_fields) or validation_failures or required_fields_missing


def convert_to_csv_format(mef_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert MeF data to expected CSV format matching the original table"""
    
    csv_data = {
        'Company': mef_data.get('BusinessNameLine1Txt', ''),
        'NAICS_Code': mef_data.get('BusinessActivityCodeTxt', ''),
        'Start_Date': '',  # Not typically on Form 1120S
        'TAX_RETURN_2021': mef_data.get('GrossReceiptsOrSalesAmt', 0),
        'Revenue': mef_data.get('GrossReceiptsOrSalesAmt', 0),
        'Gross_Profit': mef_data.get('GrossProfitAmt', 0),
        'Net_Profit': mef_data.get('OrdinaryBusinessIncomeAmt', 0),
        'Interest': mef_data.get('InterestDeductionAmt', 0),
        'Depreciation': mef_data.get('DepreciationAmt', 0),
        'Amortization': 0,  # Need to extract from statements
        'Rent': 0,  # Need to extract from line 11
        'EIN': mef_data.get('EIN', ''),
        'Comments': ''
    }
    
    return csv_data