import io
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from docx import Document
import fitz  # PyMuPDF
import pymupdf
from groq import Groq

st.set_page_config(page_title="Groq File to Markdown", page_icon="📝", layout="wide")

st.title("📝 File to Markdown Converter")
st.caption("Upload a document, convert its contents into clean Markdown with Groq, preview it, and download the .md file.")

MODEL_OPTIONS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
]

def get_api_key():
    try:
        key = st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        key = ""
    return key or os.getenv("GROQ_API_KEY", "")

def extract_pdf(data: bytes) -> str:
    pages = []
    with fitz.open(stream=data, filetype="pdf") as pdf:
        for page_no, page in enumerate(pdf, start=1):
            text = page.get_text("text")
            if text.strip():
                pages.append(f"\n\n--- Page {page_no} ---\n{text}")
    return "\n".join(pages)

def extract_docx(data: bytes) -> str:
    doc = Document(io.BytesIO(data))
    parts = []
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            parts.append(paragraph.text)
    for table_no, table in enumerate(doc.tables, start=1):
        parts.append(f"\nTable {table_no}:")
        for row in table.rows:
            parts.append(" | ".join(cell.text.replace("\n", " ").strip() for cell in row.cells))
    return "\n".join(parts)

def extract_file(uploaded_file) -> str:
    data = uploaded_file.getvalue()
    suffix = Path(uploaded_file.name).suffix.lower()

    if suffix == ".pdf":
        return extract_pdf(data)
    if suffix == ".docx":
        return extract_docx(data)
    if suffix in {".txt", ".md"}:
        return data.decode("utf-8", errors="replace")
    if suffix == ".csv":
        df = pd.read_csv(io.BytesIO(data))
        return df.to_string(index=False)
    if suffix in {".xlsx", ".xls"}:
        sheets = pd.read_excel(io.BytesIO(data), sheet_name=None)
        output = []
        for sheet_name, df in sheets.items():
            output.append(f"Sheet: {sheet_name}\n{df.to_string(index=False)}")
        return "\n\n".join(output)
    raise ValueError(f"Unsupported file type: {suffix}")

def split_text(text: str, max_chars: int = 14000):
    """Split long extracted text into manageable chunks, preferring paragraph boundaries."""
    chunks, current = [], ""
    for paragraph in text.splitlines():
        candidate = (current + "\n" + paragraph).strip()
        if len(candidate) > max_chars and current:
            chunks.append(current)
            current = paragraph
        else:
            current = candidate
        while len(current) > max_chars:
            chunks.append(current[:max_chars])
            current = current[max_chars:]
    if current.strip():
        chunks.append(current)
    return chunks

def convert_with_groq(text: str, client: Groq, model: str, instruction: str):
    chunks = split_text(text)
    converted = []
    progress = st.progress(0, text="Preparing conversion...")
    for i, chunk in enumerate(chunks, start=1):
        response = client.chat.completions.create(
            model=model,
            temperature=0.1,
            max_completion_tokens=6000,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert document-to-Markdown converter. "
                        "Convert the supplied source into valid, readable GitHub-flavored Markdown. "
                        "Preserve all factual information, names, numbers, dates, formulas, and meaning. "
                        "Do not invent missing content. Use meaningful headings, lists, tables, and code "
                        "fences where appropriate. Return only Markdown, with no prefatory commentary."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Conversion instructions: {instruction}\n\n"
                        f"Convert source chunk {i} of {len(chunks)}. Preserve its content faithfully:\n\n"
                        f"{chunk}"
                    ),
                },
            ],
        )
        converted.append(response.choices[0].message.content or "")
        progress.progress(i / len(chunks), text=f"Converted chunk {i} of {len(chunks)}")
    progress.empty()
    return "\n\n".join(converted)

with st.sidebar:
    st.header("Conversion settings")
    model = st.selectbox("Groq model", MODEL_OPTIONS, index=0)
    instruction = st.text_area(
        "Additional instructions",
        value="Organize the document clearly. Keep important details and use tables when the source contains tabular data.",
        height=120,
    )
    st.caption("The API key is read from Streamlit Secrets or the GROQ_API_KEY environment variable.")

uploaded = st.file_uploader(
    "Choose a file",
    type=["pdf", "docx", "txt", "md", "csv", "xlsx", "xls"],
    help="Supported formats: PDF, DOCX, TXT, MD, CSV and Excel.",
)

if uploaded:
    st.write(f"**Selected file:** {uploaded.name} · {uploaded.size / 1024:.1f} KB")
    if st.button("Convert to Markdown", type="primary", use_container_width=True):
        api_key = get_api_key()
        if not api_key:
            st.error("Groq API key not found. Add GROQ_API_KEY to .streamlit/secrets.toml or your environment.")
            st.stop()
        try:
            with st.spinner("Extracting document text..."):
                source_text = extract_file(uploaded)
            if not source_text.strip():
                st.error("No readable text was found. If this is a scanned PDF, run OCR first and upload the searchable PDF.")
                st.stop()

            st.info(f"Extracted {len(source_text):,} characters.")
            client = Groq(api_key=api_key)
            markdown = convert_with_groq(source_text, client, model, instruction)
            st.session_state["converted_markdown"] = markdown
            st.session_state["output_name"] = f"{Path(uploaded.name).stem}.md"
            st.success("Conversion completed.")
        except Exception as exc:
            st.error(f"Conversion failed: {exc}")

if st.session_state.get("converted_markdown"):
    st.divider()
    st.subheader("Markdown preview")
    markdown = st.session_state["converted_markdown"]
    tab_preview, tab_source = st.tabs(["Rendered preview", "Markdown source"])
    with tab_preview:
        st.markdown(markdown)
    with tab_source:
        st.code(markdown, language="markdown")
    st.download_button(
        "⬇️ Download Markdown",
        data=markdown.encode("utf-8"),
        file_name=st.session_state.get("output_name", "converted.md"),
        mime="text/markdown",
        type="primary",
        use_container_width=True,
    )

st.divider()
st.caption("Note: Scanned/image-only PDFs need OCR before conversion. Large files are split into chunks; each chunk is processed as a separate Groq request.")
