/**
 * Client-side PDF text extraction using pdfjs-dist.
 * Run in browser only; used before saving to Supabase.
 */
import * as pdfjsLib from "pdfjs-dist";
// Vite: resolve worker URL from our app code so the worker loads correctly
// @ts-expect-error - Vite handles ?url for worker
import pdfjsWorker from "pdfjs-dist/build/pdf.worker.mjs?url";
pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorker;

const PDF_MIME = "application/pdf";
const MAX_SIZE_MB = 10;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

export interface ParseResult {
  text: string;
  pageCount: number;
}

/**
 * Validates that the file is a PDF and within size limit.
 */
export function validateResumeFile(file: File): { ok: true } | { ok: false; error: string } {
  if (file.type !== PDF_MIME) {
    return { ok: false, error: "File must be a PDF" };
  }
  if (file.size > MAX_SIZE_BYTES) {
    return { ok: false, error: `File must be under ${MAX_SIZE_MB}MB` };
  }
  return { ok: true };
}

/**
 * Extracts text from a PDF file (browser only).
 * Returns concatenated text from all pages and the page count.
 */
export async function parsePdfToText(file: File): Promise<ParseResult> {
  const arrayBuffer = await file.arrayBuffer();
  const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
  const pageCount = pdf.numPages;
  const pageTexts: string[] = [];

  for (let i = 1; i <= pageCount; i++) {
    const page = await pdf.getPage(i);
    const textContent = await page.getTextContent();
    const pageText = textContent.items
      .map((item) => ("str" in item ? item.str : ""))
      .join(" ");
    pageTexts.push(pageText);
  }

  const text = pageTexts.join("\n\n").trim();
  return { text, pageCount };
}
