# Medical-Report-Analyzer

![image](https://github.com/user-attachments/assets/501f1369-0782-4bc7-8013-4358d4804418)


# Medical Report Analyzer

A Flask-based web application that uses Mistral AI's OCR and LLM capabilities to extract structured medical test data from PDFs and images of medical reports.

## Features

- Upload medical reports in PDF or image format (PNG, JPG, JPEG)
- Performs OCR to extract text from documents
- Uses Mistral AI's models to extract structured medical test data
- Converts extracted data to CSV format for easy analysis
- Simple web interface for uploading documents and downloading results

## Tech Stack

- **Backend**: Flask (Python)
- **AI Services**: Mistral AI API (OCR and LLM)
- **Frontend**: HTML, CSS, JavaScript

## Installation

### Prerequisites

- Python 3.7+
- Mistral AI API key

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/SakibAhmedShuva/Medical-Report-Analyzer.git
   cd Medical-Report-Analyzer
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root with your Mistral AI API key:
   ```
   MISTRAL_API_KEY=your_mistral_api_key_here
   ```

## Usage

1. Start the Flask server:
   ```bash
   python app.py
   ```

2. Open your browser and navigate to `http://localhost:5000`

3. Upload a medical report (PDF or image format)

4. View the extracted structured data and download as CSV

## API Endpoints

- `GET /`: Main page with upload interface
- `POST /process-report`: Upload and process a medical report
- `GET /download/<filename>`: Download a processed report as CSV

## How It Works

1. The application receives an uploaded medical report file (PDF or image)
2. Using Mistral AI's OCR capabilities, the application extracts text from the document
3. The extracted text is processed by Mistral's LLM to identify medical test data
4. Structured data is extracted and standardized into a consistent format
5. Results are saved as CSV and returned to the user

## Project Structure

```
Medical-Report-Analyzer/
├── app.py               # Main Flask application
├── .env                 # Environment variables (API keys)
├── requirements.txt     # Python dependencies
├── templates/           # HTML templates
│   └── index.html       # Main page template
└── results/             # Folder to store generated CSV files
```

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgements

- [Mistral AI](https://mistral.ai/) for OCR and LLM services
- [Flask](https://flask.palletsprojects.com/) web framework
