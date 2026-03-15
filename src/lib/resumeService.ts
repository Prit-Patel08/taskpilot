/**
 * Resume upload (Supabase Storage) and persist parsed text (Supabase DB).
 * All calls are from the client using the existing Supabase client.
 */
import { supabase } from "@/lib/supabaseClient";
import { parsePdfToText, validateResumeFile } from "@/lib/resumeParser";

const BUCKET = "resumes";

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

/**
 * 1. Validates file (PDF, size).
 * 2. Uploads PDF to Storage at path {userId}/{fileName}.
 * 3. Parses PDF to text in the browser.
 * 4. Upserts row in public.resumes (one row per user).
 * Requires an authenticated user (userId from auth).
 */
export async function uploadResume(
  userId: string,
  file: File
): Promise<UploadResumeResult | UploadResumeError> {
  const validation = validateResumeFile(file);
  if (!validation.ok) {
    return { success: false, error: validation.error };
  }

  const fileName = file.name.replace(/[^a-zA-Z0-9._-]/g, "_");
  const storagePath = `${userId}/${fileName}`;

  const { error: uploadError } = await supabase.storage
    .from(BUCKET)
    .upload(storagePath, file, { upsert: true });

  if (uploadError) {
    return { success: false, error: uploadError.message };
  }

  const { text } = await parsePdfToText(file);

  const row = {
    user_id: userId,
    file_name: fileName,
    storage_path: storagePath,
    file_size_bytes: file.size,
    parsed_text: text || null,
    updated_at: new Date().toISOString(),
  };

  const { data, error } = await supabase
    .from("resumes")
    .upsert(row, { onConflict: "user_id" })
    .select()
    .single();

  if (error) {
    return { success: false, error: error.message };
  }

  return { success: true, resume: data as ResumeRow };
}

/**
 * Fetches the current user's resume row (if any).
 */
export async function getResume(userId: string): Promise<ResumeRow | null> {
  const { data, error } = await supabase
    .from("resumes")
    .select("*")
    .eq("user_id", userId)
    .maybeSingle();

  if (error) {
    console.error("getResume error:", error);
    return null;
  }

  return data as ResumeRow | null;
}
