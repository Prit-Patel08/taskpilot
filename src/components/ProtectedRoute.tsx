import { useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { getCurrentUser } from "@/lib/auth";

type ProtectedRouteProps = {
  children: React.ReactNode;
};

/**
 * Protects routes that require authentication.
 * If the user is not logged in, redirects to /login.
 * Shows nothing (or a loader) while checking session.
 */
export const ProtectedRoute = ({ children }: ProtectedRouteProps) => {
  const [user, setUser] = useState<unknown>(undefined);
  const [loading, setLoading] = useState(true);
  const location = useLocation();

  useEffect(() => {
    let cancelled = false;

    getCurrentUser().then((u) => {
      if (!cancelled) {
        setUser(u);
        setLoading(false);
      }
    });

    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-pulse text-muted-foreground">Loading...</div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};
