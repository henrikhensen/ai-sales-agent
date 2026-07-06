"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import {
  AUTH_UNAUTHORIZED_EVENT,
  clearAuthToken,
  getAuthToken,
  getCurrentUser,
  loginUser,
  registerUser,
  setAuthToken,
} from "@/lib/api";
import type { LoginRequest, RegisterRequest, User } from "@/lib/types";

interface AuthContextValue {
  currentUser: User | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (payload: LoginRequest) => Promise<void>;
  register: (payload: RegisterRequest) => Promise<User>;
  logout: () => void;
  refreshCurrentUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshCurrentUser = useCallback(async () => {
    if (!getAuthToken()) {
      setCurrentUser(null);
      setLoading(false);
      return;
    }
    try {
      const user = await getCurrentUser();
      setCurrentUser(user);
    } catch {
      // Token missing, invalid, expired, or the account no longer exists:
      // drop it so the rest of the app treats this as logged out.
      clearAuthToken();
      setCurrentUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  // Runs once on mount, client-side only — never touches localStorage
  // during server rendering or static generation.
  useEffect(() => {
    refreshCurrentUser();
  }, [refreshCurrentUser]);

  // A 401 from any request (e.g. an access token that expired mid-session)
  // clears the stored token in lib/api.ts and fires this event; clearing
  // currentUser here makes RequireAuth/RequireRole redirect to /login on
  // their next render, without every page having to handle 401 itself.
  useEffect(() => {
    function handleUnauthorized() {
      setCurrentUser(null);
    }
    window.addEventListener(AUTH_UNAUTHORIZED_EVENT, handleUnauthorized);
    return () => {
      window.removeEventListener(AUTH_UNAUTHORIZED_EVENT, handleUnauthorized);
    };
  }, []);

  const login = useCallback(async (payload: LoginRequest) => {
    const token = await loginUser(payload);
    setAuthToken(token.access_token);
    const user = await getCurrentUser();
    setCurrentUser(user);
  }, []);

  const register = useCallback(async (payload: RegisterRequest) => {
    return registerUser(payload);
  }, []);

  const logout = useCallback(() => {
    clearAuthToken();
    setCurrentUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        currentUser,
        loading,
        isAuthenticated: currentUser !== null,
        login,
        register,
        logout,
        refreshCurrentUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
