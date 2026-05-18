import { Navigate } from "react-router-dom";

import { LoginForm } from "@/components/auth/LoginForm";
import { Card } from "@/components/ui/card";
import { useAuth } from "@/hooks/useAuth";

export function LoginPage() {
  const { session, loading } = useAuth();

  if (loading) {
    return <div className="p-8 text-center">Loading…</div>;
  }
  if (session) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-md p-6">
        <h1 className="mb-6 text-center text-2xl font-semibold">Sign in</h1>
        <LoginForm />
      </Card>
    </div>
  );
}
