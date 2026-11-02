"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import {
  clearStoredToken,
  getStoredToken,
  setStoredToken,
} from "@/lib/token";
import { getCurrentUser, loginUser, registerUser } from "@/services/api";
import type { AuthUser } from "@/types";

type AuthContextValue = {
  user: AuthUser | null;
  isLoading: boolean;
  error: string | null;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

type AuthProviderProps = {
  children: React.ReactNode;
};

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadSession() {
      const token = getStoredToken();
      if (!token) {
        setIsLoading(false);
        return;
      }

      try {
        const currentUser = await getCurrentUser(token);
        if (!active) {
          return;
        }
        setUser({ id: currentUser.id, email: currentUser.email ?? null });
        setError(null);
      } catch {
        if (!active) {
          return;
        }
        clearStoredToken();
        setUser(null);
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    }

    void loadSession();

    return () => {
      active = false;
    };
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const auth = await loginUser({ email, password });
    setStoredToken(auth.access_token);
    setUser(auth.user);
    setError(null);
  }, []);

  const signUp = useCallback(async (email: string, password: string) => {
    const auth = await registerUser({ email, password });
    setStoredToken(auth.access_token);
    setUser(auth.user);
    setError(null);
  }, []);

  const signOut = useCallback(async () => {
    clearStoredToken();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({
      user,
      isLoading,
      error,
      signIn,
      signUp,
      signOut,
    }),
    [user, isLoading, error, signIn, signUp, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
