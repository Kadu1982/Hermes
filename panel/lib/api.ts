export const API_BASE =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_HERMES_API) ||
  "http://127.0.0.1:8000/api/v1";

const TOKEN_KEY = "hermes_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(t: string) {
  localStorage.setItem(TOKEN_KEY, t);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

/** Limpa sessão e redireciona ao login (token expirado ou JWT inválido). */
export function handleAuthFailure(detail?: string) {
  clearToken();
  if (typeof window === "undefined") return;
  const msg = detail || "Sessão expirada ou inválida. Faça login de novo (email + senha + código 2FA).";
  sessionStorage.setItem("hermes_login_message", msg);
  window.location.href = "/";
}

export async function apiFetch(path: string, init: RequestInit = {}) {
  const token = getToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(init.headers || {}),
  };
  if (token) (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (res.status === 401 && typeof window !== "undefined") {
    let detail = "Invalid token";
    try {
      const body = await res.clone().json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* ignore */
    }
    handleAuthFailure(
      detail === "Invalid token"
        ? "Token inválido ou expirado. Saia e entre de novo com admin@example.com e o código 2FA."
        : detail
    );
  }
  return res;
}
