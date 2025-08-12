import argparse
import re
import pandas as pd
import spacy
from tqdm import tqdm
import pdfplumber
from fpdf import FPDF
import sys

# --- NLP Model and Constants ---

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Spacy model 'en_core_web_sm' not found. Please run 'python -m spacy download en_core_web_sm'", file=sys.stderr)
    sys.exit(1)

CODE_PATTERNS = [
    r'\b(ASTM\s+[A-Z0-9-]+)\b',
    r'\b(ISO\s+\d+)\b',
    r'\b(BS\s+EN\s+\d+)\b',
    r'\b(BS\s+\d+)\b',
    r'\b(EN\s+\d+)\b',
    r'\b(AASHTO\s+[A-Z0-9-]+)\b',
]

DEFAULT_MATERIALS = [
    "concrete", "steel", "cement", "asphalt", "aggregate", "brick", "timber",
    "glass", "plastic", "aluminum", "copper", "epoxy", "grout",
    "waterproofing membrane", "geotextile", "rebar", "structural steel"
]

# --- Helper Functions (to be implemented) ---

def extract_text_from_pdf(pdf_path):
    """Extracts text from each page of a PDF file."""
    pages_content = {}
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                # Ensure text is not None
                text = page.extract_text()
                if text:
                    pages_content[i + 1] = text
    except FileNotFoundError:
        print(f"Error: The file at {pdf_path} was not found.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred while processing the PDF: {e}", file=sys.stderr)
        sys.exit(1)
    return pages_content

def setup_material_matcher(custom_materials=None):
    """Sets up the spacy Matcher with material patterns."""
    from spacy.matcher import Matcher
    matcher = Matcher(nlp.vocab)

    # Combine default and custom materials, ensuring no duplicates
    all_materials = set(DEFAULT_MATERIALS + (custom_materials or []))

    for material in all_materials:
        # Create a pattern for each material. This handles multi-word materials.
        pattern = [{"LOWER": word} for word in material.lower().split()]
        matcher.add(material.replace(" ", "_").upper(), [pattern])

    return matcher

def extract_by_regex(patterns, text):
    """Finds all occurrences of a list of regex patterns in a text."""
    findings = set()
    for pattern in patterns:
        try:
            matches = re.findall(pattern, text)
            findings.update(matches)
        except re.error as e:
            print(f"Regex error with pattern '{pattern}': {e}", file=sys.stderr)
    return list(findings)

def classify_material_type(name, context):
    """Classifies the material type based on its name and context."""
    name_lower = name.lower()

    # Simple keyword-based classification logic
    if any(k in name_lower for k in ['concrete', 'cement', 'grout']):
        return "Cementitious"
    if any(k in name_lower for k in ['steel', 'rebar', 'aluminum', 'copper', 'metal']):
        return "Metallic"
    if any(k in name_lower for k in ['asphalt', 'bitumen']):
        return "Bituminous"
    if any(k in name_lower for k in ['plastic', 'polymer', 'epoxy', 'geotextile', 'pvc']):
        return "Polymeric"
    if any(k in name_lower for k in ['wood', 'timber']):
        return "Wood-based"
    if 'glass' in name_lower:
        return "Glass-based"
    if any(k in name_lower for k in ['brick', 'aggregate', 'stone', 'sand', 'masonry']):
        return "Masonry/Aggregate"
    if 'membrane' in name_lower:
        return "Waterproofing/Membrane"

    return "Other/Unclassified"

def export_to_pdf(df, output_path="Extracted_Technical_Spec_Report.pdf"):
    """Exports a DataFrame to a PDF report, truncating long text to fit."""
    pdf = FPDF(orientation='L')
    pdf.add_page()
    pdf.set_font("Arial", size=8)

    col_widths = {
        'Sl. No.': 15,
        'Material Name': 35,
        'Specific Material Type': 35,
        'Specific Standard Specification': 75,
        'Code/Standard': 40,
        'Any other relevant information': 55
    }
    line_height = pdf.font_size * 2

    # Header
    pdf.set_font(style='B')
    for col_name in df.columns:
        pdf.cell(col_widths[col_name], line_height, col_name, border=1, align='C')
    pdf.ln(line_height)
    pdf.set_font(style='')

    # Data rows
    for _, row in df.iterrows():
        for col_name in df.columns:
            text = str(row[col_name])
            # Simple truncation based on character length as a fallback
            max_len = int(col_widths[col_name] / 1.8) # Estimate max chars
            if len(text) > max_len:
                text = text[:max_len-3] + '...'
            pdf.cell(col_widths[col_name], line_height, text, border=1, align='L')
        pdf.ln(line_height)

    try:
        pdf.output(output_path)
    except Exception as e:
        print(f"Failed to generate PDF report at {output_path}: {e}", file=sys.stderr)

def clean_csv_for_export(df):
    """Cleans the DataFrame for CSV export by replacing newlines in cells."""
    df_copy = df.copy()
    for col in df_copy.select_dtypes(include=['object']):
        # Replace newlines with a space to ensure clean CSV formatting
        df_copy[col] = df_copy[col].str.replace('\n', ' | ', regex=False)
    return df_copy

def compute_extraction_precision_recall(df, ground_truth_df):
    """
    Computes precision, recall, and F1 score against a ground truth.
    - True Positive (TP): A material is in both extracted and ground truth, and their codes overlap.
    - False Positive (FP): A material was extracted that is not in the ground truth, or codes don't match.
    - False Negative (FN): A material in the ground truth was not extracted.
    """
    # Normalize data for comparison
    def normalize_codes(codes_str):
        if pd.isna(codes_str) or "No Information" in codes_str:
            return set()
        # Split by ' | ' and strip whitespace from each code
        return {code.strip() for code in codes_str.split(' | ') if code.strip()}

    extracted_data = {
        row['Material Name'].strip().lower(): normalize_codes(row['Code/Standard'])
        for _, row in df.iterrows()
    }
    truth_data = {
        row['Material Name'].strip().lower(): normalize_codes(row['Code/Standard'])
        for _, row in ground_truth_df.iterrows()
    }

    extracted_materials = set(extracted_data.keys())
    truth_materials = set(truth_data.keys())

    tp = 0
    # Iterate through materials that are in both sets
    for material in extracted_materials.intersection(truth_materials):
        extracted_codes = extracted_data[material]
        truth_codes = truth_data[material]

        # If both expect no codes, it's a true positive for that material.
        if not truth_codes and not extracted_codes:
            tp += 1
        # If there is at least one matching code, count it as a true positive.
        elif truth_codes.intersection(extracted_codes):
            tp += 1

    fp = len(extracted_materials) - tp
    fn = len(truth_materials) - tp

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return precision, recall, f1

# --- Main Analysis Function ---

def analyze_specification_document(pdf_path, custom_materials=None):
    print("1. Extracting text from PDF...")
    try:
        pages_content = extract_text_from_pdf(pdf_path)
    except Exception as e:
        print(f"Error extracting text from PDF: {e}", file=sys.stderr)
        return pd.DataFrame()

    final_output = []

    print("2. Setting up material matcher...")
    matcher = setup_material_matcher(custom_materials)
    material_mentions = {}

    print("3. Finding and grouping material mentions...")
    for page, text in tqdm(pages_content.items()):
        doc = nlp(text)
        matches = matcher(doc)
        for match_id, start, end in matches:
            name = doc[start:end].text.strip().lower()
            sentence = doc[start:end].sent.text.strip()

            if name not in material_mentions:
                material_mentions[name] = []
            material_mentions[name].append({'page': page, 'sentence': sentence, 'full_page_context': text})

    print("4. Analyzing each material for specific specifications and codes...")
    for name, mentions in tqdm(material_mentions.items()):
        unique_pages = sorted(list(set(m['page'] for m in mentions)))

        specific_spec = "No Information Available"
        relevant_codes = set()

        # First, search for codes in the specific sentence of each mention
        for mention in mentions:
            codes_in_sentence = extract_by_regex(CODE_PATTERNS, mention['sentence'])
            if codes_in_sentence:
                relevant_codes.update(codes_in_sentence)
                # If a spec hasn't been found yet, take the first sentence that contains a code
                if specific_spec == "No Information Available":
                    specific_spec = mention['sentence']

        # If no codes were found in any sentence, search the full page context of each mention
        if not relevant_codes:
            for mention in mentions:
                relevant_codes.update(extract_by_regex(CODE_PATTERNS, mention['full_page_context']))

        # As a fallback for spec, if no sentence had a code, take the first mention's sentence
        if specific_spec == "No Information Available" and mentions:
            specific_spec = mentions[0]['sentence']

        full_context = " ".join(m['full_page_context'] for m in mentions)
        material_type = classify_material_type(name, full_context)

        codes_str = "\n".join(f"- {c}" for c in sorted(list(relevant_codes))) if relevant_codes else "No Information Available"

        final_output.append({
            "Material Name": name.title(),
            "Specific Material Type": material_type,
            "Specific Standard Specification": specific_spec,
            "Code/Standard": codes_str,
            "Any other relevant information": f"Found on pages: {', '.join(map(str, unique_pages))}"
        })

    if not final_output:
        print("No materials found in the document.")
        return pd.DataFrame()

    df = pd.DataFrame(final_output)
    df.insert(0, 'Sl. No.', range(1, 1 + len(df)))
    df = df[['Sl. No.', 'Material Name', 'Specific Material Type', 'Specific Standard Specification', 'Code/Standard', 'Any other relevant information']]
    return df

# --- Main Execution Block ---

def main():
    parser = argparse.ArgumentParser(description="Analyze a technical specification PDF to extract material information.")
    parser.add_argument("pdf_path", help="Path to the technical specification PDF file.")
    parser.add_argument("--ground_truth", help="Path to the ground truth Excel file for evaluation.", default=None)
    parser.add_argument("--custom_materials", help="Comma-separated list of custom materials to search for.", default="")

    args = parser.parse_args()

    custom_materials_list = [term.strip() for term in args.custom_materials.split(",") if term.strip()]

    print("\nStarting analysis... this may take a moment.")
    df = analyze_specification_document(args.pdf_path, custom_materials_list)

    if not df.empty:
        print("\nAnalysis Complete. Preview of Extracted Data:")
        print(df.head())

        pdf_report_path = "Extracted_Technical_Spec_Report.pdf"
        print(f"\nGenerating PDF report at {pdf_report_path}...")
        export_to_pdf(df, pdf_report_path)

        csv_report_path = "Extracted_Technical_Spec_Report.csv"
        print(f"\nGenerating CSV report at {csv_report_path}...")
        df_cleaned = clean_csv_for_export(df)
        df_cleaned.to_csv(csv_report_path, index=False)

        print(f"\nReports generated successfully.")

        if args.ground_truth:
            try:
                print(f"\n--- Loading ground truth file from {args.ground_truth} ---")
                ground_truth_df = pd.read_excel(args.ground_truth, engine='openpyxl')
                print("--- Comparing extracted data with ground truth... ---")
                precision, recall, f1 = compute_extraction_precision_recall(df, ground_truth_df)

                print(f"\n✅ Evaluation Metrics:")
                print(f"Precision: {precision:.2%}")
                print(f"   Recall: {recall:.2%}")
                print(f" F1 Score: {f1:.2%}")
            except FileNotFoundError:
                print(f"\nError: Ground truth file not found at {args.ground_truth}", file=sys.stderr)
            except Exception as e:
                print(f"\nAn error occurred during evaluation: {e}", file=sys.stderr)

    else:
        print("\nAnalysis finished, but no data was extracted to generate reports.")

if __name__ == "__main__":
    main()
