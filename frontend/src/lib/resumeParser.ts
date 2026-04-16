/**
 * Client-side resume validation only.
 * Parsing and storage are intentionally backend-owned in the production architecture.
 */

const PDF_MIME = "application/pdf";
const MAX_SIZE_MB = 10;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

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
