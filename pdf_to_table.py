"""
PDF Text Extraction and Tabular Conversion Tool

This script extracts text and tables from PDFs and converts them into
CSV format with automatic table detection and manual column mapping.

Usage:
    python pdf_to_table.py <input_pdf> [--output output.csv] [--interactive]

Features:
    - Automatic table detection using pdfplumber
    - Text-based PDF support (selectable text)
    - Manual column mapping for unstructured text
    - CSV export
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import pdfplumber
import pandas as pd
import re


class PDFTableExtractor:
    def __init__(self, pdf_path: str):
        """Initialize the PDF extractor with a file path."""
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        self.pdf = pdfplumber.open(pdf_path)
        self.tables = []
        self.raw_text = ""

    @staticmethod
    def extract_right_number(line: str) -> tuple:
        """
        Extract a number from the right side of a text line.
        Returns (text, number) tuple. If no number found, number is None.
        
        Examples:
            "Item Name        $50.00" -> ("Item Name", "$50.00")
            "Description  123.45" -> ("Description", "123.45")
            "No number here" -> ("No number here", None)
        """
        # Look for numbers (including currency symbols and decimals) at the end
        # Pattern: optional whitespace, optional currency symbol, numbers with optional decimals, end of line
        match = re.search(r'\s+([$€£¥₹]?\d+[.,]\d{2}|\d+)\s*$', line)
        
        if match:
            number = match.group(1).strip()
            text = line[:match.start()].strip()
            return text, number
        
        return line.strip(), None

    def extract_tables(self) -> List[pd.DataFrame]:
        """Extract all tables from the PDF automatically."""
        all_tables = []
        for page_num, page in enumerate(self.pdf.pages, 1):
            tables = page.extract_tables()
            if tables:
                for table_num, table in enumerate(tables):
                    df = pd.DataFrame(table[1:], columns=table[0])
                    df = self._clean_dataframe(df)
                    df.insert(0, "Page", page_num)
                    df.insert(1, "Table", table_num + 1)
                    all_tables.append(df)
                    print(f"✓ Extracted table from page {page_num}, table #{table_num + 1}")
        self.tables = all_tables
        return all_tables

    def extract_raw_text(self) -> str:
        """Extract raw text from all pages."""
        text = ""
        for page_num, page in enumerate(self.pdf.pages, 1):
            page_text = page.extract_text()
            if page_text:
                text += f"\n--- Page {page_num} ---\n{page_text}"
        self.raw_text = text
        return text

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean extracted dataframe by removing empty rows/columns."""
        # Remove empty columns
        df = df.dropna(axis=1, how='all')
        # Remove empty rows
        df = df.dropna(axis=0, how='all')
        # Strip whitespace from all cells
        df = df.applymap(lambda x: str(x).strip() if pd.notna(x) else x)
        return df

    def parse_structured_text(self) -> pd.DataFrame:
        """
        Attempt to parse raw text into structured format.
        Looks for common patterns like rows of data separated by newlines.
        """
        if not self.raw_text:
            self.extract_raw_text()

        lines = self.raw_text.split('\n')
        lines = [l.strip() for l in lines if l.strip() and not l.startswith('---')]

        if not lines:
            return pd.DataFrame()

        # Try to detect if lines contain consistent delimiters
        data = []
        for line in lines:
            # Split by multiple spaces (common in text files)
            parts = re.split(r'\s{2,}', line)
            if len(parts) > 1:
                data.append(parts)

        if data:
            # Use the first line as potential headers
            max_cols = max(len(row) for row in data)
            headers = [f"Column {i+1}" for i in range(max_cols)]

            df = pd.DataFrame(data, columns=headers[:len(data[0])])
            return self._clean_dataframe(df)

        return pd.DataFrame()

    def interactive_column_mapping(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Allow user to manually map or rename columns interactively.
        """
        print("\n" + "="*60)
        print("COLUMN MAPPING")
        print("="*60)
        print(f"Found {len(df.columns)} columns in extracted data:")
        for i, col in enumerate(df.columns, 1):
            print(f"  {i}. {col}")

        print("\nEnter new names for columns (or press Enter to keep existing name)")
        print("Example: Press Enter to skip, or type 'Date' to rename\n")

        new_columns = {}
        for col in df.columns:
            user_input = input(f"Rename '{col}': ").strip()
            if user_input:
                new_columns[col] = user_input
            else:
                new_columns[col] = col

        df.rename(columns=new_columns, inplace=True)
        return df

    def close(self):
        """Close the PDF file."""
        self.pdf.close()


def main():
    parser = argparse.ArgumentParser(
        description="Extract text from PDF and convert to tabular CSV format"
    )
    parser.add_argument("pdf_file", help="Path to the PDF file")
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output CSV file path (default: input_filename.csv)"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Enable interactive column mapping"
    )
    parser.add_argument(
        "--no-auto-detect",
        action="store_true",
        help="Skip automatic table detection, parse as raw text only"
    )

    args = parser.parse_args()

    # Validate input
    pdf_path = Path(args.pdf_file).resolve()
    if not pdf_path.exists():
        print(f"❌ Error: PDF file not found: {pdf_path}")
        sys.exit(1)

    # Determine output file (same directory as input PDF by default)
    if args.output:
        output_path = Path(args.output).resolve()
    else:
        output_path = pdf_path.parent / (pdf_path.stem + ".csv")

    print(f"📄 Processing: {pdf_path.name}")
    print(f"💾 Output file: {output_path.name}")
    print("-" * 60)

    try:
        extractor = PDFTableExtractor(str(pdf_path))

        # Extract tables if not disabled
        dfs_to_export = []
        if not args.no_auto_detect:
            tables = extractor.extract_tables()
            if tables:
                print(f"\n✓ Found {len(tables)} table(s) in PDF")
                dfs_to_export = tables
            else:
                print("⚠ No structured tables found. Attempting to parse raw text...")
                df = extractor.parse_structured_text()
                if not df.empty:
                    dfs_to_export = [df]
                    print(f"✓ Parsed raw text into table with {len(df.columns)} columns")
        else:
            print("Parsing PDF as raw text...")
            df = extractor.parse_structured_text()
            if not df.empty:
                dfs_to_export = [df]

        if not dfs_to_export:
            # Fallback: extract raw text as rows with optional number extraction
            print("⚠ Could not parse as structured table. Converting raw text to rows...")
            text = extractor.extract_raw_text()
            print(f"✓ Extracted {len(text)} characters of text")
            
            # Split text into rows (each line becomes a row)
            lines = text.split('\n')
            lines = [l.strip() for l in lines if l.strip() and not l.startswith('---')]
            
            if lines:
                # Attempt to extract numbers from right side of text
                rows = []
                has_numbers = False
                for line in lines:
                    text_part, number_part = PDFTableExtractor.extract_right_number(line)
                    if number_part:
                        has_numbers = True
                    rows.append({'Text': text_part, 'Value': number_part})
                
                # If numbers were detected, ask user if they want to keep them separated
                if has_numbers:
                    text_df = pd.DataFrame(rows)
                    print(f"✓ Detected {sum(1 for r in rows if r['Value'] is not None)} lines with numbers on the right")
                    print(f"✓ Converted {len(lines)} lines to text and value rows")
                else:
                    text_df = pd.DataFrame({'Text': lines})
                    print(f"✓ Converted {len(lines)} lines to text rows")
                
                dfs_to_export = [text_df]
            else:
                print("\n❌ No text could be extracted from PDF.")
                extractor.close()
                return

        # Combine all dataframes
        combined_df = pd.concat(dfs_to_export, ignore_index=True)

        # Interactive column mapping if requested
        if args.interactive:
            combined_df = extractor.interactive_column_mapping(combined_df)

        # Show preview
        print("\n" + "="*60)
        print("PREVIEW OF EXTRACTED DATA")
        print("="*60)
        print(combined_df.to_string(max_rows=10, max_colwidth=30))
        if len(combined_df) > 10:
            print(f"... and {len(combined_df) - 10} more rows")

        # Save to CSV
        combined_df.to_csv(output_path, index=False, quoting=csv.QUOTE_MINIMAL)
        print(f"\n✓ Successfully exported {len(combined_df)} rows to {output_path.name}")
        print(f"✓ Columns: {', '.join(combined_df.columns)}")

        extractor.close()

    except Exception as e:
        print(f"\n❌ Error processing PDF: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
