/**
 * Client-side: fetch jobs from Supabase for the Jobs dashboard page.
 */
import { supabase } from "./supabaseClient";

export interface Job {
  id: string;
  external_id: string;
  source: string;
  company: string;
  title: string;
  location: string | null;
  description: string | null;
  apply_url: string;
  created_at: string;
}

export async function getJobs(): Promise<Job[]> {
  const { data, error } = await supabase
    .from("jobs")
    .select("id, external_id, source, company, title, location, description, apply_url, created_at")
    .order("created_at", { ascending: false });

  if (error) {
    console.error("getJobs error:", error);
    throw error;
  }

  return (data ?? []) as Job[];
}
