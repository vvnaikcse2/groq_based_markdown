# Groq File to Markdown Converter

A Streamlit application that extracts content from PDF, DOCX, TXT, MD, CSV, and Excel files, then uses the Groq API to produce structured Markdown.

## 1. Get a Groq API key
Create an API key at https://console.groq.com/keys.

## 2. Install dependencies
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

## 3. Configure the API key

Create `.streamlit/secrets.toml` and add:
```toml
GROQ_API_KEY = "your_actual_key"
```

Do not commit this file to GitHub. Alternatively, set the `GROQ_API_KEY` environment variable.

## 4. Run locally
```bash
streamlit run app.py
```

## 5. Deploy on Streamlit Community Cloud
1. Push `app.py`, `requirements.txt`, `.gitignore`, and `README.md` to a GitHub repository.
2. Open https://share.streamlit.io/ and create a new app from that repository.
3. Set the main file path to `app.py`.
4. In the app's **Settings → Secrets**, add:
   ```toml
   GROQ_API_KEY = "your_actual_key"
   ```
5. Deploy the app.

## Supported inputs
- PDF (text-based/searchable PDFs)
- DOCX
- TXT and MD
- CSV
- XLSX and XLS

Scanned PDFs require OCR before upload. Large documents are divided into chunks and converted in multiple Groq requests.
