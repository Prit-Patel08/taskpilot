const rawApiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "";
const apiBaseUrl = rawApiBaseUrl.replace(/\/$/, "");

const CONTENT_TYPE_BY_EXTENSION: Record<string, string> = {
  ".pdf": "application/pdf",
  ".docx":
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
};

export class ApiError extends Error {
  readonly status: number;
  readonly body: unknown;

  constructor(message: string, status: number, body?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

function buildApiUrl(path: string): string {
  if (/^https?:\/\//.test(path)) {
    return path;
  }

  return `${apiBaseUrl}${path}`;
}

function extractErrorMessage(body: unknown, fallback: string): string {
  if (body && typeof body === "object") {
    const record = body as Record<string, unknown>;
    const detail = record.detail ?? record.error ?? record.message;

    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
  }

  if (typeof body === "string" && body.trim()) {
    return body;
  }

  return fallback;
}

export function isPlaceholderApiError(error: unknown): error is ApiError {
  return (
    error instanceof ApiError &&
    (error.status === 0 || error.status === 404 || error.status === 501)
  );
}

export function toApiErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    return error.message;
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallback;
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  const isFormData = init.body instanceof FormData;

  if (init.body !== undefined && !isFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;

  try {
    response = await fetch(buildApiUrl(path), {
      ...init,
      headers,
    });
  } catch {
    throw new ApiError(
      "Backend API is unavailable. Start the backend service or implement the placeholder endpoint.",
      0,
    );
  }

  const contentType = response.headers.get("content-type") ?? "";
  let body: unknown = null;

  if (response.status !== 204) {
    if (contentType.includes("application/json")) {
      body = await response.json().catch(() => null);
    } else {
      body = await response.text().catch(() => null);
    }
  }

  if (!response.ok) {
    throw new ApiError(
      extractErrorMessage(body, `Request failed with status ${response.status}`),
      response.status,
      body,
    );
  }

  return body as T;
}

export interface PresignedUploadResponse {
  upload_url: string;
  object_key: string;
  file_url: string;
  expires_in: number;
  max_upload_size_bytes: number;
  upload_headers: Record<string, string>;
}

export interface ApplicationResponse {
  application_id: string;
  status: string;
  user_id?: string;
  resume_url?: string;
  created_at?: string;
  score?: number;
  score_breakdown?: Record<string, unknown>;
}

export function getUploadContentType(file: File): string {
  const lowerName = file.name.toLowerCase();
  const matchingExtension = Object.keys(CONTENT_TYPE_BY_EXTENSION).find((extension) =>
    lowerName.endsWith(extension),
  );

  if (!matchingExtension) {
    throw new Error("Unsupported file type. Please upload a PDF or DOCX file.");
  }

  const expectedContentType = CONTENT_TYPE_BY_EXTENSION[matchingExtension];
  const normalizedType = file.type.trim().toLowerCase();

  if (normalizedType && normalizedType !== expectedContentType) {
    throw new Error(
      "File content type does not match the selected file extension. Please choose a valid PDF or DOCX file.",
    );
  }

  return expectedContentType;
}

export async function getPresignedUrl(
  file: File,
): Promise<PresignedUploadResponse> {
  return apiRequest<PresignedUploadResponse>("/v1/uploads/presign", {
    method: "POST",
    body: JSON.stringify({
      filename: file.name,
      content_type: getUploadContentType(file),
      file_size_bytes: file.size,
    }),
  });
}

export async function createApplication(
  resumeUrl: string,
  idempotencyKey: string = crypto.randomUUID(),
): Promise<ApplicationResponse> {
  return apiRequest<ApplicationResponse>("/v1/applications", {
    method: "POST",
    headers: {
      "Idempotency-Key": idempotencyKey,
      "X-Request-ID": crypto.randomUUID(),
    },
    body: JSON.stringify({
      resume_url: resumeUrl,
    }),
  });
}

export async function getApplication(
  applicationId: string,
): Promise<ApplicationResponse> {
  return apiRequest<ApplicationResponse>(
    `/v1/applications/${encodeURIComponent(applicationId)}`,
    {
      headers: {
        "X-Request-ID": crypto.randomUUID(),
      },
    },
  );
}
