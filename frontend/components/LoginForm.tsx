"use client";

import { useState } from "react";

import { useAuth } from "@/components/AuthProvider";

export function LoginForm() {
  const { signIn, signUp, error: authError } = useAuth();
  const [mode, setMode] = useState<"sign-in" | "sign-up">("sign-in");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      if (mode === "sign-in") {
        await signIn(email, password);
      } else {
        await signUp(email, password);
      }
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message.replace(/^Error:\s*/i, "")
          : mode === "sign-in"
            ? "Sign in failed"
            : "Creating the account failed",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  const message = error ?? authError;

  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <section className="w-full max-w-md rounded-lg border border-slate-800 bg-slate-900 p-8">
        <p className="text-xs font-medium uppercase tracking-widest text-indigo-400">
          NudgeOps
        </p>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight text-slate-50">
          {mode === "sign-in" ? "Sign in" : "Create account"}
        </h1>
        <p className="mt-2 text-sm text-slate-400">
          {mode === "sign-in"
            ? "Sign in to run Kubernetes investigations."
            : "Register with an email and password to get started."}
        </p>

        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
          <label className="block text-sm font-medium text-slate-300">
            Email
            <input
              className="mt-1.5 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 placeholder-slate-600 outline-none transition-colors focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/40"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>
          <label className="block text-sm font-medium text-slate-300">
            Password
            <input
              className="mt-1.5 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 placeholder-slate-600 outline-none transition-colors focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/40"
              type="password"
              autoComplete={
                mode === "sign-in" ? "current-password" : "new-password"
              }
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              minLength={8}
              required
            />
          </label>

          {message && <p className="text-sm text-red-400">{message}</p>}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-md bg-indigo-500 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-indigo-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
          >
            {isSubmitting
              ? "Please wait..."
              : mode === "sign-in"
                ? "Sign in"
                : "Create account"}
          </button>
        </form>

        <button
          type="button"
          onClick={() => {
            setMode(mode === "sign-in" ? "sign-up" : "sign-in");
            setError(null);
          }}
          className="mt-5 text-sm font-medium text-slate-400 transition-colors hover:text-slate-200"
        >
          {mode === "sign-in"
            ? "Need an account? Sign up"
            : "Already have an account? Sign in"}
        </button>
      </section>
    </main>
  );
}
