"use client";

import { useAuth } from "@/components/AuthProvider";
import { Dashboard } from "@/components/Dashboard";
import { LoginForm } from "@/components/LoginForm";

export default function HomePage() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center px-6">
        <p className="text-sm text-slate-500">Loading authentication...</p>
      </main>
    );
  }

  if (!user) {
    return <LoginForm />;
  }

  return <Dashboard />;
}
