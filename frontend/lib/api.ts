const DEFAULT_BASE = "http://127.0.0.1:8000";

export function getApiBase(): string {
  if (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_API_BASE_URL.replace(/\/$/, "");
  }
  return DEFAULT_BASE;
}

export function apiUrl(path: string): string {
  const base = getApiBase();
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${base}${p}`;
}

export type SkillRow = {
  name: string;
  path: string;
  location: string;
  description: string;
};

export type MemoryRow = {
  session_id: string;
  path_md: string;
  path_json: string;
  updated_at: string;
};

async function handleJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export async function fetchHealth(): Promise<{ status: string }> {
  const res = await fetch(apiUrl("/health"), { cache: "no-store" });
  return handleJson(res);
}

export type TavilyRecentCall = {
  at: string;
  query_preview: string;
  success: boolean;
  tokens_delta: number;
  error: string | null;
  result_count: number | null;
};

export type TavilyUsage = {
  configured: boolean;
  total_queries: number;
  total_tokens: number;
  total_errors: number;
  recent_calls: TavilyRecentCall[];
};

/** 聚合用量；未配置 Tavily 时 `tavily.configured` 为 false。 */
export type UsageResponse = {
  tavily: TavilyUsage;
};

export async function fetchUsage(): Promise<UsageResponse> {
  const res = await fetch(apiUrl("/api/usage"), { cache: "no-store" });
  return handleJson(res);
}

export async function fetchSkillsList(): Promise<{ skills: SkillRow[] }> {
  const res = await fetch(apiUrl("/api/skills"), { cache: "no-store" });
  return handleJson(res);
}

export async function fetchSkillFile(path: string): Promise<{ path: string; content: string }> {
  const q = new URLSearchParams({ path });
  const res = await fetch(`${apiUrl("/api/skills")}?${q}`, { cache: "no-store" });
  return handleJson(res);
}

export async function saveSkill(path: string, content: string): Promise<void> {
  const res = await fetch(apiUrl("/api/skills"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path, content }),
  });
  await handleJson(res);
}

export async function reloadSkills(): Promise<void> {
  const res = await fetch(apiUrl("/api/skills/reload"), { method: "POST" });
  await handleJson(res);
}

export async function fetchMemoriesList(): Promise<{ memories: MemoryRow[] }> {
  const res = await fetch(apiUrl("/api/memories"), { cache: "no-store" });
  return handleJson(res);
}

export async function fetchMemoryFile(path: string): Promise<{ path: string; content: string }> {
  const q = new URLSearchParams({ path });
  const res = await fetch(`${apiUrl("/api/memories")}?${q}`, { cache: "no-store" });
  return handleJson(res);
}

export async function saveMemory(path: string, content: string): Promise<void> {
  const res = await fetch(apiUrl("/api/memories"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path, content }),
  });
  await handleJson(res);
}

export async function fetchSessions(): Promise<{ sessions: MemoryRow[] }> {
  const res = await fetch(apiUrl("/api/sessions"), { cache: "no-store" });
  return handleJson(res);
}

export type ChatJsonResponse = {
  session_id: string;
  output: string;
};

export async function postChatSync(body: {
  message: string;
  session_id: string;
  stream: false;
}): Promise<ChatJsonResponse> {
  const res = await fetch(apiUrl("/api/chat"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return handleJson(res);
}

export function postChatStreamRequest(body: {
  message: string;
  session_id: string;
  stream: true;
}): Promise<Response> {
  return fetch(apiUrl("/api/chat"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
