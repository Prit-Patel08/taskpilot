import { supabase } from "./supabaseClient";
import type { User } from "@supabase/supabase-js";

/**
 * Fetches the current authenticated user from Supabase.
 * Use this to check auth state (e.g. in ProtectedRoute or navbar).
 */
export async function getCurrentUser(): Promise<User | null> {
  const {
    data: { user },
    error,
  } = await supabase.auth.getUser();

  if (error) {
    console.error("Auth get user error:", error.message);
    return null;
  }

  return user;
}
