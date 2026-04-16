from __future__ import annotations

from io import BytesIO
from zipfile import BadZipFile, ZipFile

import pdfplumber
from docx import Document

from app.errors.domain_errors import ParseFailed, UnsupportedFormat


def _is_pdf(file_bytes: bytes) -> bool:
    return file_bytes.startswith(b"%PDF")


def _is_docx(file_bytes: bytes) -> bool:
    if not file_bytes.startswith(b"PK"):
        return False

    try:
        with ZipFile(BytesIO(file_bytes)) as archive:
            return "word/document.xml" in archive.namelist()
    except BadZipFile:
        return False


def _extract_pdf_text(file_bytes: bytes) -> str:
    try:
        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            text_chunks = [
                page_text.strip()
                for page in pdf.pages
                if (page_text := page.extract_text())
                and page_text.strip()
            ]
    except Exception as exc:  # pragma: no cover - parser library errors vary
        raise ParseFailed("Failed to extract text from PDF resume") from exc

    extracted_text = "\n\n".join(text_chunks).strip()
    if not extracted_text:
        raise ParseFailed("PDF resume did not contain extractable text")
    return extracted_text


def _extract_docx_text(file_bytes: bytes) -> str:
    try:
        document = Document(BytesIO(file_bytes))
    except Exception as exc:  # pragma: no cover - parser library errors vary
        raise ParseFailed("Failed to extract text from DOCX resume") from exc

    text_chunks = [
        paragraph.text.strip()
        for paragraph in document.paragraphs
        if paragraph.text and paragraph.text.strip()
    ]
    extracted_text = "\n".join(text_chunks).strip()
    if not extracted_text:
        raise ParseFailed("DOCX resume did not contain extractable text")
    return extracted_text


def extract_text(file_bytes: bytes) -> str:
    if not file_bytes:
        raise ParseFailed("Resume file was empty")

    if _is_pdf(file_bytes):
        return _extract_pdf_text(file_bytes)

    if _is_docx(file_bytes):
        return _extract_docx_text(file_bytes)

    raise UnsupportedFormat("Resume format is unsupported; only PDF and DOCX are allowed")
