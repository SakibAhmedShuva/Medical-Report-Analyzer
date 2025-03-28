from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import base64
from pathlib import Path
import tempfile
import json
import csv
import uuid
from datetime import datetime

from mistralai import Mistral
from mistralai import DocumentURLChunk, ImageURLChunk, TextChunk
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv("MISTRAL_API_KEY")
if not api_key:
    raise ValueError("MISTRAL_API_KEY not found in .env file")

# Initialize Mistral client
client = Mistral(api_key=api_key)

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Configure upload settings
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
TEMP_FOLDER = tempfile.gettempdir()
RESULTS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")

# Create results folder if it doesn't exist
if not os.path.exists(RESULTS_FOLDER):
    os.makedirs(RESULTS_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_pdf(file_path):
    """Process a PDF file with OCR"""
    pdf_file = Path(file_path)
    
    # Upload PDF file to Mistral's OCR service
    uploaded_file = client.files.upload(
        file={
            "file_name": pdf_file.stem,
            "content": pdf_file.read_bytes(),
        },
        purpose="ocr",
    )
    
    # Get URL for the uploaded file
    signed_url = client.files.get_signed_url(file_id=uploaded_file.id, expiry=1)
    
    # Process PDF with OCR
    pdf_response = client.ocr.process(
        document=DocumentURLChunk(document_url=signed_url.url),
        model="mistral-ocr-latest"
    )
    
    # Extract markdown from all pages
    all_markdown = ""
    for page in pdf_response.pages:
        all_markdown += page.markdown + "\n\n"
    
    return all_markdown

def process_image(file_path):
    """Process an image file with OCR"""
    image_file = Path(file_path)
    
    # Encode image as base64 for API
    encoded = base64.b64encode(image_file.read_bytes()).decode()
    base64_data_url = f"data:image/jpeg;base64,{encoded}"
    
    # Process image with OCR
    image_response = client.ocr.process(
        document=ImageURLChunk(image_url=base64_data_url),
        model="mistral-ocr-latest"
    )
    
    # Extract markdown from the page
    return image_response.pages[0].markdown

def extract_structured_data(ocr_markdown):
    """Extract structured medical test data from OCR results"""
    
    # Use Mistral to extract structured data
    chat_response = client.chat.complete(
        model="pixtral-12b-latest",
        messages=[
            {
                "role": "user",
                "content": [
                    TextChunk(
                        text=(
                            f"This is a medical report's OCR in markdown:\n\n{ocr_markdown}\n\n"
                            "Extract all medical test information in a structured JSON format. "
                            "For each test, include only: test_name, test_value, test_unit, reference_value, reference_unit. "
                            "If any field is missing, use null. "
                            "The output should be strictly JSON with no extra commentary."
                        )
                    ),
                ],
            }
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    
    # Parse JSON response
    try:
        response_dict = json.loads(chat_response.choices[0].message.content)
        
        # Ensure uniform format
        standardized_response = {
            "medical_tests": []
        }
        
        # Process the response to ensure uniform structure
        if isinstance(response_dict, dict):
            # Handle different possible response structures
            if "tests" in response_dict:
                tests = response_dict["tests"]
            elif "medical_tests" in response_dict:
                tests = response_dict["medical_tests"]
            else:
                # Assume the response is already a list of tests or a dict of tests
                tests = response_dict.get("results", response_dict)
                
            if isinstance(tests, list):
                for test in tests:
                    standardized_response["medical_tests"].append({
                        "test_name": test.get("test_name", test.get("name", None)),
                        "test_value": test.get("test_value", test.get("value", None)),
                        "test_unit": test.get("test_unit", test.get("unit", None)),
                        "reference_value": test.get("reference_value", test.get("reference_range", test.get("reference", None))),
                        "reference_unit": test.get("reference_unit", test.get("ref_unit", None))
                    })
            elif isinstance(tests, dict):
                # Handle case where tests are a dictionary
                for name, details in tests.items():
                    if isinstance(details, dict):
                        standardized_response["medical_tests"].append({
                            "test_name": name,
                            "test_value": details.get("value", details.get("Value", None)),
                            "test_unit": details.get("unit", details.get("Unit", None)),
                            "reference_value": details.get("reference_value", details.get("reference", details.get("reference_range", None))),
                            "reference_unit": details.get("reference_unit", details.get("ref_unit", None))
                        })
                    else:
                        standardized_response["medical_tests"].append({
                            "test_name": name,
                            "test_value": details,
                            "test_unit": None,
                            "reference_value": None,
                            "reference_unit": None
                        })
        
        return standardized_response
        
    except json.JSONDecodeError:
        return {"error": "Failed to parse structured data", "medical_tests": []}

def save_to_csv(data, filename):
    """Save medical test data to CSV file"""
    filepath = os.path.join(RESULTS_FOLDER, filename)
    
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['test_name', 'test_value', 'test_unit', 'reference_value', 'reference_unit']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for test in data["medical_tests"]:
            writer.writerow({
                'test_name': test.get('test_name', ''),
                'test_value': test.get('test_value', ''),
                'test_unit': test.get('test_unit', ''),
                'reference_value': test.get('reference_value', ''),
                'reference_unit': test.get('reference_unit', '')
            })
    
    return filepath

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process-report', methods=['POST'])
def process_report():
    # Check if file is in the request
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    
    # Check if filename is empty
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    # Check if file type is allowed
    if not allowed_file(file.filename):
        return jsonify({"error": f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"}), 400
    
    try:
        # Save file temporarily
        filename = secure_filename(file.filename)
        file_path = os.path.join(TEMP_FOLDER, filename)
        file.save(file_path)
        
        # Process file based on type
        file_extension = filename.rsplit('.', 1)[1].lower()
        
        if file_extension == 'pdf':
            ocr_markdown = process_pdf(file_path)
        else:  # image file
            ocr_markdown = process_image(file_path)
        
        # Extract structured data
        structured_data = extract_structured_data(ocr_markdown)
        
        # Generate unique filename for CSV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        csv_filename = f"medical_report_{timestamp}_{unique_id}.csv"
        
        # Save to CSV
        csv_path = save_to_csv(structured_data, csv_filename)
        
        # Add CSV filename to response
        structured_data["csv_filename"] = csv_filename
        
        # Clean up temporary file
        os.remove(file_path)
        
        return jsonify(structured_data)
    
    except Exception as e:
        # Clean up temporary file if it exists
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        
        return jsonify({"error": str(e)}), 500

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    """Download a CSV file"""
    try:
        return send_file(os.path.join(RESULTS_FOLDER, filename),
                         mimetype='text/csv',
                         as_attachment=True,
                         download_name=filename)
    except Exception as e:
        return jsonify({"error": str(e)}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
