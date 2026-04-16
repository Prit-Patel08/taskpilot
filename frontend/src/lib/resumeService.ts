/**
 * Resume flows are backend-driven.
 * The frontend validates the file and sends it only to backend API placeholders.
 */
import { validateResumeFile } from "@/lib/resumeParser";
import {
  apiRequest,
  isPlaceholderApiError,
  toApiErrorMessage,
} from "@/services/api";

export interface ResumeRow {
  id: string;
  user_id: string;
  file_name: string;
  storage_path: string;
  file_size_bytes: number | null;
  parsed_text: string | null;
  created_at: string;
  updated_at: string;
}

export interface UploadResumeResult {
  success: true;
  resume: ResumeRow;
}

export interface UploadResumeError {
  success: false;
  error: string;
}

export async function uploadResume(
  userId: string,
  file: File
): Promise<UploadResumeResult | UploadResumeError> {
  const validation = validateResumeFile(file);
  if (!validation.ok) {
    return { success: false, error: validation.error };
  }

  const payload = new FormData();
  payload.append("user_id", userId);
  payload.append("file", file);

  try {
    const data = await apiRequest<{ resume: ResumeRow }>("/v1/resumes", {
      method: "POST",
      body: payload,
    });

    return { success: true, resume: data.resume };
  } catch (error) {
    if (isPlaceholderApiError(error)) {
      return {
        success: false,
        error:
          "TODO: Backend resume ingestion endpoint is not implemented yet.",
      };
    }

    return {
      success: false,
      error: toApiErrorMessage(error, "Failed to upload resume"),
    };
  }
}

export async function getResume(userId: string): Promise<ResumeRow | null> {
  try {
    const data = await apiRequest<{ resume: ResumeRow | null }>(
      `/v1/resumes/${encodeURIComponent(userId)}`,
    );
    return data.resume ?? null;
  } catch (error) {
    if (isPlaceholderApiError(error)) {
      return null;
    }

    console.error("getResume error:", error);
    return null;
  }
}
