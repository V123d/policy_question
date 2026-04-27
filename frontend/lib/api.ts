const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Token = string | null;

function getAccessToken(): Token {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

function setTokens(access: string, refresh: string) {
  localStorage.setItem("access_token", access);
  localStorage.setItem("refresh_token", refresh);
}

function clearTokens() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

function getHeaders(includeAuth = true): HeadersInit {
  const headers: HeadersInit = { "Content-Type": "application/json" };
  if (includeAuth) {
    const token = getAccessToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }
  return headers;
}

class TokenRefreshedError extends Error {
  constructor() {
    super("Token refreshed, retry");
    this.name = "TokenRefreshedError";
  }
}

async function handleResponse<T>(res: Response, url?: string): Promise<T> {
  if (res.status === 401) {
    console.log("[handleResponse] 401 from", url, "- attempting token refresh");
    const refreshed = await refreshAccessToken();
    if (!refreshed) {
      clearTokens();
      console.log("[handleResponse] token refresh failed - clearing tokens");
      throw new Error("Unauthorized");
    }
    console.log("[handleResponse] token refreshed successfully");
    throw new TokenRefreshedError();
  }
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || "Request failed");
  }
  return res.json();
}

async function refreshAccessToken(): Promise<boolean> {
  const refresh = localStorage.getItem("refresh_token");
  if (!refresh) return false;
  try {
    const res = await fetch(`${API_BASE}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    localStorage.setItem("access_token", data.access_token);
    return true;
  } catch {
    return false;
  }
}

export const api = {
  auth: {
    login: async (username: string, password: string) => {
      const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const data = await handleResponse<{
        access_token: string;
        refresh_token: string;
        user: User;
      }>(res);
      setTokens(data.access_token, data.refresh_token);
      return data;
    },
    register: async (username: string, password: string, role = "user") => {
      const res = await fetch(`${API_BASE}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password, role }),
      });
      return handleResponse<User>(res);
    },
    me: async (): Promise<User> => {
      const res = await fetch(`${API_BASE}/api/auth/me`, {
        headers: getHeaders(),
      });
      if (res.status === 401) {
        const refreshed = await refreshAccessToken();
        if (refreshed) {
          const retryRes = await fetch(`${API_BASE}/api/auth/me`, {
            headers: getHeaders(),
          });
          if (retryRes.ok) return retryRes.json();
        }
        clearTokens();
        throw new Error("Unauthorized");
      }
      if (!res.ok) {
        const error = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(error.detail || "Request failed");
      }
      return res.json();
    },
    logout: () => {
      clearTokens();
    },
  },

  policies: {
    list: async (params?: { status?: string; skip?: number; limit?: number }): Promise<Policy[]> => {
      const qs = new URLSearchParams();
      if (params?.status) qs.set("status", params.status);
      if (params?.skip) qs.set("skip", String(params.skip));
      if (params?.limit) qs.set("limit", String(params.limit));
      const res = await fetch(`${API_BASE}/api/policies?${qs}`, { headers: getHeaders(false) });
      return handleResponse<Policy[]>(res);
    },
    get: async (id: string): Promise<Policy> => {
      const res = await fetch(`${API_BASE}/api/policies/${id}`, { headers: getHeaders(false) });
      return handleResponse<Policy>(res);
    },
    getStructured: async (id: string): Promise<PolicyStructured> => {
      const res = await fetch(`${API_BASE}/api/policies/${id}/structured`, { headers: getHeaders(false) });
      return handleResponse<PolicyStructured>(res);
    },
    search: async (keyword: string): Promise<Policy[]> => {
      const res = await fetch(`${API_BASE}/api/policies/search/keyword?keyword=${encodeURIComponent(keyword)}`, {
        headers: getHeaders(false),
      });
      return handleResponse<Policy[]>(res);
    },
    timeline: async (): Promise<TimelineItem[]> => {
      const res = await fetch(`${API_BASE}/api/policies/timeline/all`, { headers: getHeaders(false) });
      return handleResponse<TimelineItem[]>(res);
    },
  },

  chat: {
    ask: async (question: string, sessionId?: string, modelProvider?: string): Promise<ChatAskResponse> => {
      const makeRequest = async () => {
        const res = await fetch(`${API_BASE}/api/chat/ask`, {
          method: "POST",
          headers: getHeaders(),
          body: JSON.stringify({ question, session_id: sessionId, model_provider: modelProvider }),
        });
        return handleResponse<ChatAskResponse>(res);
      };
      try {
        return await makeRequest();
      } catch (e) {
        if (e instanceof TokenRefreshedError) return makeRequest();
        throw e;
      }
    },
    askStream: async (
      question: string,
      onChunk: (delta: string) => void,
      sessionId?: string,
      modelProvider?: string,
      onDone?: (cited: CitedPolicy[]) => void,
      abortController?: AbortController
    ): Promise<string | undefined> => {
      const makeStreamRequest = async (): Promise<Response> => {
        const token = getAccessToken();
        return fetch(`${API_BASE}/api/chat/ask/stream`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ question, session_id: sessionId, model_provider: modelProvider }),
          signal: abortController?.signal,
        });
      };

      let res = await makeStreamRequest();
      console.log("[askStream] response status:", res.status, "url:", `${API_BASE}/api/chat/ask/stream`);

      if (res.status === 401) {
        console.log("[askStream] 401 - attempting token refresh");
        const refreshed = await refreshAccessToken();
        if (!refreshed) {
          clearTokens();
          throw new Error("Unauthorized");
        }
        console.log("[askStream] token refreshed - retrying");
        res = await makeStreamRequest();
      }

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let buffer = "";
      let returnedSessionId: string | undefined;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.type === "content") {
                onChunk(data.delta);
              } else if (data.type === "done") {
                returnedSessionId = data.session_id;
                onDone?.(data.cited_policies || []);
              }
            } catch {}
          }
        }
      }
      return returnedSessionId;
    },
    getHistory: async (sessionId: string): Promise<ChatHistoryItem[]> => {
      const makeRequest = async () => {
        const res = await fetch(`${API_BASE}/api/chat/history/${sessionId}`, { headers: getHeaders() });
        return handleResponse<ChatHistoryItem[]>(res, `/api/chat/history/${sessionId}`);
      };
      try {
        return await makeRequest();
      } catch (e) {
        console.log("[getHistory] caught:", e instanceof TokenRefreshedError ? "TokenRefreshedError" : (e as Error).message);
        if (e instanceof TokenRefreshedError) return makeRequest();
        throw e;
      }
    },
    listSessions: async (): Promise<Session[]> => {
      const makeRequest = async () => {
        const res = await fetch(`${API_BASE}/api/chat/sessions`, { headers: getHeaders() });
        return handleResponse<Session[]>(res, "/api/chat/sessions");
      };
      try {
        return await makeRequest();
      } catch (e) {
        console.log("[listSessions] caught:", e instanceof TokenRefreshedError ? "TokenRefreshedError" : (e as Error).message);
        if (e instanceof TokenRefreshedError) return makeRequest();
        throw e;
      }
    },
    deleteSession: async (sessionId: string) => {
      const makeRequest = async () => {
        const res = await fetch(`${API_BASE}/api/chat/sessions/${sessionId}`, {
          method: "DELETE",
          headers: getHeaders(),
        });
        return handleResponse(res);
      };
      try {
        return await makeRequest();
      } catch (e) {
        if (e instanceof TokenRefreshedError) return makeRequest();
        throw e;
      }
    },
  },

  admin: {
    dashboard: async (): Promise<DashboardStats> => {
      const res = await fetch(`${API_BASE}/api/admin/dashboard/stats`, { headers: getHeaders() });
      return handleResponse<DashboardStats>(res);
    },
    uploadPolicy: async (file: File, onProgress?: (pct: number) => void): Promise<PolicyUploadResponse> => {
      const formData = new FormData();
      formData.append("file", file);
      const token = getAccessToken();
      const res = await fetch(`${API_BASE}/api/admin/policies/upload`, {
        method: "POST",
        headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: formData,
      });
      return handleResponse<PolicyUploadResponse>(res);
    },
    uploadPolicyText: async (name: string, rawText: string): Promise<PolicyUploadResponse> => {
      const formData = new FormData();
      formData.append("name", name);
      formData.append("raw_text", rawText);
      const token = getAccessToken();
      const res = await fetch(`${API_BASE}/api/admin/policies/upload-text`, {
        method: "POST",
        headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: formData,
      });
      return handleResponse<PolicyUploadResponse>(res);
    },
    listPolicies: async (params?: { status?: string }): Promise<Policy[]> => {
      const qs = new URLSearchParams();
      if (params?.status) qs.set("status", params.status);
      const res = await fetch(`${API_BASE}/api/admin/policies?${qs}`, { headers: getHeaders() });
      return handleResponse<Policy[]>(res);
    },
    deletePolicy: async (id: string) => {
      const res = await fetch(`${API_BASE}/api/admin/policies/${id}`, {
        method: "DELETE",
        headers: getHeaders(),
      });
      return handleResponse(res);
    },
    reparsePolicy: async (id: string): Promise<PolicyUploadResponse> => {
      const res = await fetch(`${API_BASE}/api/admin/re-parse/${id}`, {
        method: "POST",
        headers: getHeaders(),
      });
      return handleResponse<PolicyUploadResponse>(res);
    },
    listUsers: async (): Promise<User[]> => {
      const res = await fetch(`${API_BASE}/api/admin/users`, { headers: getHeaders() });
      return handleResponse<User[]>(res);
    },
    updateUserRole: async (userId: string, role: string) => {
      const res = await fetch(`${API_BASE}/api/admin/users/${userId}/role?role=${role}`, {
        method: "PATCH",
        headers: getHeaders(),
      });
      return handleResponse<User>(res);
    },
    deleteUser: async (userId: string) => {
      const res = await fetch(`${API_BASE}/api/admin/users/${userId}`, {
        method: "DELETE",
        headers: getHeaders(),
      });
      return handleResponse(res);
    },
    listQueries: async (params?: { user_id?: string; skip?: number; limit?: number }): Promise<ChatLog[]> => {
      const qs = new URLSearchParams();
      if (params?.user_id) qs.set("user_id", params.user_id);
      if (params?.skip) qs.set("skip", String(params.skip));
      if (params?.limit) qs.set("limit", String(params.limit));
      const res = await fetch(`${API_BASE}/api/admin/queries?${qs}`, { headers: getHeaders() });
      return handleResponse<ChatLog[]>(res);
    },
  },

  kg: {
    getGraph: async (): Promise<KGGraph> => {
      const res = await fetch(`${API_BASE}/api/kg/graph`, { headers: getHeaders(false) });
      return handleResponse<KGGraph>(res);
    },
    getPolicyGraph: async (id: string): Promise<KGSubgraph> => {
      const res = await fetch(`${API_BASE}/api/kg/policy/${id}`, { headers: getHeaders(false) });
      return handleResponse<KGSubgraph>(res);
    },
  },
};

export type User = {
  id: string;
  username: string;
  role: string;
  created_at: string;
};

export type Policy = {
  id: string;
  name: string;
  issuing_body?: string;
  doc_type?: string;
  policy_level?: string;
  policy_subject?: string;
  effective_date?: string;
  deadline?: string;
  status: string;
  upload_time: string;
  uploader_id?: string;
  raw_text?: string;
  structured_data: Record<string, unknown>;
};

export type PolicyStructured = {
  id: string;
  name: string;
  issuing_body?: string;
  doc_type?: string;
  policy_level?: string;
  policy_subject?: string;
  effective_date?: string;
  deadline?: string;
  consultation: Record<string, string>;
  structured_data: Record<string, unknown>;
};

export type TimelineItem = {
  id: string;
  name: string;
  deadline?: string;
  effective_date?: string;
  issuing_body?: string;
  doc_type?: string;
  structured_data_keys: string[];
};

export type ChatAskResponse = {
  answer: string;
  session_id: string;
  cited_policies: CitedPolicy[];
};

export type CitedPolicy = {
  policy_id: string;
  policy_name: string;
  reason?: string;
};

export type ChatHistoryItem = {
  id: string;
  session_id?: string;
  user_id?: string;
  question: string;
  answer?: string;
  cited_policies: CitedPolicy[];
  created_at: string;
};

export type Session = {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
};

export type DashboardStats = {
  total_policies: number;
  active_policies: number;
  parsing_policies: number;
  failed_policies: number;
  total_users: number;
  total_chats: number;
  chats_today: number;
  chats_this_week: number;
  parse_success_rate: number;
};

export type PolicyUploadResponse = {
  id: string;
  name: string;
  status: string;
  doc_type?: string;
  policy_level?: string;
  message: string;
};

export type ChatLog = {
  id: string;
  session_id?: string;
  user_id?: string;
  question: string;
  answer?: string;
  model_provider?: string;
  model_name?: string;
  tokens_used?: number;
  response_time_ms?: number;
  cited_policies: CitedPolicy[];
  created_at: string;
};

export type KGGraph = {
  nodes: KGNode[];
  edges: KGEdge[];
};

export type KGNode = {
  id: string;
  node_type: string;
  name: string;
  policy_id?: string;
  node_data: Record<string, unknown>;
};

export type KGEdge = {
  id: string;
  source_id: string;
  target_id: string;
  relation: string;
  source_policy_id?: string;
  target_policy_id?: string;
};

export type KGSubgraph = {
  nodes: KGNode[];
  edges: KGEdge[];
  policy: Policy;
};
