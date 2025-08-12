# Technical Specification Document Analyzer

This script analyzes technical specification documents in PDF format to extract information about materials, their specifications, and relevant codes or standards.

## Features

- Extracts text from PDF documents.
- Identifies mentions of various technical materials (e.g., concrete, steel).
- Finds associated codes and standards (e.g., ASTM, ISO).
- Classifies materials into types (e.g., Cementitious, Metallic).
- Generates reports in both PDF and CSV formats.
- Evaluates the extraction accuracy against a ground truth file.

## Setup

1.  **Clone the repository or download the files.**

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install the required Python packages:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Download the spaCy language model:**
    ```bash
    python -m spacy download en_core_web_sm
    ```

## Usage

You can run the script from the command line.

### Basic Usage

To analyze a PDF file, provide the path to the file:

```bash
python document_analyzer.py /path/to/your/document.pdf
```

### With Custom Materials

To search for specific materials in addition to the default list, use the `--custom_materials` flag:

```bash
python document_analyzer.py /path/to/your/document.pdf --custom_materials "stainless steel,pvc pipe"
```

### With Evaluation

To evaluate the results against a ground truth file (in `.xlsx` format), use the `--ground_truth` flag:

```bash
python document_analyzer.py /path/to/your/document.pdf --ground_truth /path/to/your/ground_truth.xlsx
```

## Outputs

The script will generate the following files in the same directory where you run the command:

-   `Extracted_Technical_Spec_Report.pdf`: A summary report in PDF format. Text in cells may be truncated to fit.
-   `Extracted_Technical_Spec_Report.csv`: A detailed report in CSV format with the full extracted text.

The script will also print a preview of the extracted data and the evaluation metrics (if a ground truth file is provided) to the console.
