# text_correction
App built in streamlit for CSV data correction and PDF charge comparison

## Features

### 1. Service Name Correction
- Upload a CSV with Service, Service Code, Provider columns
- Automatically detects inconsistent service names using fuzzy matching
- Allows batch corrections and downloads corrected CSV

### 2. PDF vs Excel Charge Comparison
- Compare charges from OCR'd PDF documents with Excel files
- Extracts charges from text-based PDF lists (date, code, description, quantity, charge)
- Matches records with fuzzy logic
- Highlights exact matches, items needing review, and unmatched charges

## Installation

```bash
pip install pandas streamlit rapidfuzz networkx pdfplumber openpyxl
```

## Usage

```bash
streamlit run app.py
```

## PDF Format Requirements

PDFs should contain a list of charges with the following information per entry:
- Date (MM/DD/YYYY format)
- Code/Reference
- Description
- Quantity
- Charge Amount

The app will extract text and allow you to map which columns contain each field.