## PDF to Table Extractor

A standalone Python tool to extract text from PDFs and convert them into CSV format.

### Features

✨ **Automatic Table Detection** - Detects and extracts structured tables from PDFs  
📝 **Raw Text Parsing** - Converts unstructured text into tabular format  
🎯 **Manual Column Mapping** - Rename columns interactively  
💾 **CSV Export** - Save extracted data as clean CSV files  
🔍 **Preview Mode** - View extracted data before saving  

### Requirements

```bash
pip install pdfplumber pandas
```

### Installation

The script `pdf_to_table.py` is already in your text_correction folder.

### Usage

#### Basic Usage - Extract Tables
```bash
python pdf_to_table.py documents.pdf
```
This automatically:
- Detects tables in the PDF
- Extracts all tables to structured format
- Saves as `documents.csv` **in the same directory as the PDF**

#### Save to Custom Location/Filename
```bash
python pdf_to_table.py input.pdf --output extracted_data.csv
```
Output is saved where you specify, or in the same directory as the PDF if using a relative path.

#### Interactive Column Mapping
```bash
python pdf_to_table.py input.pdf --interactive
```
Allows you to rename columns after extraction for better clarity.

#### Parse Raw Text (No Table Detection)
```bash
python pdf_to_table.py input.pdf --no-auto-detect
```
Better for unstructured PDFs where text should be parsed by whitespace delimiters.

#### Full Example
```bash
python pdf_to_table.py invoice.pdf --output invoice_data.csv --interactive
```

### Smart Number Extraction

When extracting unstructured text, the tool **automatically detects and separates numbers on the right side** of lines.

**Supported formats:**
- Currency amounts: `$50.00`, `€100.50`, `£25.99`
- Plain numbers: `123`, `45.67`, `1,234.56`
- Any currency symbol: $, €, £, ¥, ₹

**Example:**
```
Input PDF text:
"Medical Service Provider ABC        $1,250.00"
"Consultation fees                   $500.00"
"Monthly subscription                $99.99"

Output CSV:
Text                                Value
"Medical Service Provider ABC"       "$1,250.00"
"Consultation fees"                  "$500.00"
"Monthly subscription"               "$99.99"
```

Use `--interactive` mode to rename the "Value" column to something more meaningful like "Amount", "Charge", "Total", etc.

### Output

The tool creates a CSV file with:
- **Page**: Page number where data was extracted (when applicable)
- **Table**: Table number on that page (when applicable)
- **Column 1, Column 2, ...**: Extracted data columns

If you use `--interactive`, you'll be prompted to rename columns during extraction.

### How It Works

1. **Table Detection Phase**: Uses pdfplumber to find structured tables
2. **Text Parsing Phase**: If no tables found, attempts to parse raw text by whitespace delimiters
3. **Fallback Phase**: If parsing fails, outputs each line as a text row in CSV format
4. **Column Mapping Phase**: (Optional with `--interactive`) Rename columns
5. **CSV Export Phase**: Saves the DataFrame as clean CSV

### Fallback Behavior

If the tool cannot detect a table structure or parse by whitespace delimiters, it automatically falls back to:
- **Extracting each line of text as a separate row** in a "Text" column
- **Automatically detecting and extracting numbers on the right** side of text into a "Value" column
- This allows you to still get a CSV output that can be post-processed or edited manually
- No data is lost—all text is preserved for further work

Example fallback output (with automatic number extraction):
```
Text                                Value
"Item Description 1"                 "$50.00"
"Item Description 2"                 "$75.50"
"Some text without number"           (empty)
```

The tool intelligently detects numbers, currency symbols ($£€¥₹), and decimal formats.

### Limitations

- ✅ Works best with **text-based PDFs** (not scanned images)
- ✅ For **scanned PDFs**, consider using OCR tools first
- ✅ Complex multi-format PDFs may need manual post-processing
- ✅ Fallback mode outputs raw text—can be cleaned up in Excel or your text_correction app

### Example Scenarios

**Scenario 1: PDF with Structured Tables**
```bash
python pdf_to_table.py financial_report.pdf
# Output: financial_report.csv with all tables combined
```

**Scenario 2: PDF with Text Lists (like charge details)**
```bash
python pdf_to_table.py charges.pdf --no-auto-detect --interactive
# Parses text, then prompts for column names
```

**Scenario 3: Processing Batch of PDFs**
```bash
for pdf in *.pdf; do
    python pdf_to_table.py "$pdf" --output "${pdf%.pdf}.csv"
done
```

### Troubleshooting

**No data extracted?**
- Check if PDF is text-based (can select text) vs scanned image
- Try `--no-auto-detect` to force raw text parsing

**Tool outputs text as rows instead of structured table?**
- This is the fallback behavior—each line becomes a row in CSV
- Numbers on the right automatically separated into "Value" column
- You can then clean this up in Excel or with your text_correction app
- Use `--interactive` to rename columns (e.g., "Value" → "Amount") after extraction

**Incorrect column detection?**
- Use `--interactive` to rename columns
- Check the preview output before saving

**Output columns are misaligned?**
- PDFs with inconsistent formatting may need manual post-processing in the CSV
- Edit the CSV file in Excel or your spreadsheet app to finalize

### Next Steps

💡 **Combine with your text_correction app:**
```bash
# 1. Extract from PDF
python pdf_to_table.py vendor_charges.pdf --output charges.csv

# 2. Clean up in text_correction app
streamlit run app.py
```

This creates a workflow: PDF → CSV → Validation & Correction
