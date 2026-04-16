import {
  apiRequest,
  isPlaceholderApiError,
  toApiErrorMessage,
} from "@/services/api";

export interface AuthenticatedUser {
  id: string;
  email: string | null;
}

interface AuthSessionResponse {
  user: AuthenticatedUser | null;
}

function authPlaceholderMessage(action: string): string {
  return `TODO: Backend-managed Auth0 ${action} endpoint is not implemented yet.`;
}

export async function getCurrentUser(): Promise<AuthenticatedUser | null> {
  try {
    const response = await apiRequest<AuthSessionResponse>("/v1/auth/session");
    return response.user ?? null;
  } catch (error) {
    if (isPlaceholderApiError(error)) {
      return null;
    }

    console.error("Auth session check error:", error);
    return null;
  }
}

export async function login(email: string, password: string): Promise<void> {
  try {
    await apiRequest<void>("/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  } catch (error) {
    if (isPlaceholderApiError(error)) {
      throw new Error(authPlaceholderMessage("login"));
    }

    throw new Error(toApiErrorMessage(error, "Failed to sign in"));
  }
}

export async function signup(email: string, password: string): Promise<void> {
  try {
    await apiRequest<void>("/v1/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  } catch (error) {
    if (isPlaceholderApiError(error)) {
      throw new Error(authPlaceholderMessage("signup"));
    }

    throw new Error(toApiErrorMessage(error, "Failed to create account"));
  }
}

export async function logout(): Promise<void> {
  try {
    await apiRequest<void>("/v1/auth/logout", {
      method: "POST",
    });
  } catch (error) {
    if (isPlaceholderApiError(error)) {
      throw new Error(authPlaceholderMessage("logout"));
    }

    throw new Error(toApiErrorMessage(error, "Failed to sign out"));
  }
}
