"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Database,
  MessageSquare,
  RefreshCw,
  Save,
  Sparkles,
} from "lucide-react";
import { MonacoEditorPanel } from "@/components/monaco-editor-panel";
import {
  apiUrl,
  fetchHealth,
  fetchMemoriesList,
  fetchMemoryFile,
  fetchSessions,
  fetchSkillFile,
  fetchSkillsList,
  fetchUsage,
  postChatStreamRequest,
  postChatSync,
  saveMemory,
  saveSkill,
  type MemoryRow,
  type SkillRow,
  type TavilyUsage,
} from "@/lib/api";
import { consumeSse } from "@/lib/sse-chat";
import { cn } from "@/lib/utils";

type NavKey = "chat" | "memory" | "skills";

type ChatMsg = { role: "user" | "assistant"; content: string };

export function AppShell() {
  const [nav, setNav] = useState<NavKey>("chat");
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const [sessions, setSessions] = useState<MemoryRow[]>([]);
  const [skills, setSkills] = useState<SkillRow[]>([]);
  const [memories, setMemories] = useState<MemoryRow[]>([]);
  const [sessionId, setSessionId] = useState("main_session");
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [useStream, setUseStream] = useState(true);
  const [busy, setBusy] = useState(false);
  const [thoughtsOpen, setThoughtsOpen] = useState(false);
  const [thoughtLog, setThoughtLog] = useState<string[]>([]);
  const [streamingText, setStreamingText] = useState("");

  const [editorPath, setEditorPath] = useState<string | null>(null);
  const [editorContent, setEditorContent] = useState("");
  const [editorDirty, setEditorDirty] = useState(false);
  const [tavilyUsage, setTavilyUsage] = useState<TavilyUsage | null>(null);

  const refreshUsage = useCallback(async () => {
    try {
      const { tavily } = await fetchUsage();
      setTavilyUsage(tavily);
    } catch {
      setTavilyUsage(null);
    }
  }, []);

  const refreshSessions = useCallback(async () => {
    try {
      const { sessions: s } = await fetchSessions();
      setSessions(s);
    } catch {
      setSessions([]);
    }
  }, []);

  const refreshSkills = useCallback(async () => {
    try {
      const { skills: sk } = await fetchSkillsList();
      setSkills(sk);
    } catch {
      setSkills([]);
    }
  }, []);

  const refreshMemories = useCallback(async () => {
    try {
      const { memories: m } = await fetchMemoriesList();
      setMemories(m);
    } catch {
      setMemories([]);
    }
  }, []);

  useEffect(() => {
    fetchHealth()
      .then(() => setApiOk(true))
      .catch(() => setApiOk(false));
    refreshSessions();
    refreshSkills();
    refreshMemories();
    void refreshUsage();
  }, [refreshSessions, refreshSkills, refreshMemories, refreshUsage]);

  useEffect(() => {
    if (nav === "skills") refreshSkills();
    if (nav === "memory") refreshMemories();
    if (nav === "chat") refreshSessions();
  }, [nav, refreshSkills, refreshMemories, refreshSessions]);

  const openInEditor = useCallback(
    async (path: string) => {
      try {
        const data = path.startsWith("skill/")
          ? await fetchSkillFile(path)
          : await fetchMemoryFile(path);
        setEditorPath(data.path);
        setEditorContent(data.content);
        setEditorDirty(false);
      } catch (e) {
        setThoughtLog((prev) => [
          ...prev,
          `打开失败 ${path}: ${e instanceof Error ? e.message : String(e)}`,
        ]);
      }
    },
    []
  );

  const handleSaveEditor = async () => {
    if (!editorPath) return;
    try {
      if (editorPath.startsWith("skill/")) {
        await saveSkill(editorPath, editorContent);
        await refreshSkills();
      } else {
        await saveMemory(editorPath, editorContent);
        await refreshMemories();
        await refreshSessions();
      }
      setEditorDirty(false);
    } catch (e) {
      setThoughtLog((prev) => [
        ...prev,
        `保存失败: ${e instanceof Error ? e.message : String(e)}`,
      ]);
    }
  };

  const appendThought = (line: string) => {
    setThoughtLog((prev) => [...prev, line]);
  };

  const sendChat = async () => {
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    setBusy(true);
    setThoughtLog([]);
    setStreamingText("");
    setThoughtsOpen(true);

    try {
      if (useStream) {
        const res = await postChatStreamRequest({
          message: text,
          session_id: sessionId,
          stream: true,
        });
        if (!res.ok) {
          throw new Error(await res.text());
        }
        let assistant = "";
        await consumeSse(res, (ev, data) => {
          appendThought(`[${ev}] ${JSON.stringify(data)}`);
          if (ev === "token" && typeof data.content === "string") {
            assistant += data.content;
            setStreamingText(assistant);
          }
          if (ev === "end" && typeof data.output === "string") {
            assistant = data.output;
          }
        });
        setMessages((m) => [...m, { role: "assistant", content: assistant }]);
        setStreamingText("");
        await refreshSessions();
      } else {
        const data = await postChatSync({
          message: text,
          session_id: sessionId,
          stream: false,
        });
        appendThought(`[json] ${JSON.stringify(data)}`);
        setMessages((m) => [...m, { role: "assistant", content: data.output }]);
        await refreshSessions();
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      appendThought(`[error] ${msg}`);
      setMessages((m) => [...m, { role: "assistant", content: `错误: ${msg}` }]);
    } finally {
      setBusy(false);
    }
  };

  const navBtn = (key: NavKey, label: string, Icon: typeof MessageSquare) => (
    <button
      type="button"
      onClick={() => setNav(key)}
      className={cn(
        "flex w-full items-center gap-2 rounded-md px-2 py-2 text-left text-sm transition-colors",
        nav === key ? "bg-slate-900 text-white" : "text-slate-700 hover:bg-slate-100"
      )}
    >
      <Icon className="h-4 w-4 shrink-0" />
      {label}
    </button>
  );

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50 text-slate-900">
      <aside className="flex w-56 shrink-0 flex-col border-r border-slate-200 bg-white">
        <div className="border-b border-slate-200 p-3">
          <div className="text-sm font-semibold">AceClaw</div>
          <div className="mt-1 text-xs text-slate-500">
            API: {apiUrl("")}
            {apiOk === true && (
              <span className="ml-1 text-emerald-600">· 已连接</span>
            )}
            {apiOk === false && (
              <span className="ml-1 text-red-600">· 未连接</span>
            )}
          </div>
          {tavilyUsage && (
            <div className="mt-2 rounded border border-slate-100 bg-slate-50 px-2 py-1.5 text-[11px] leading-snug text-slate-600">
              <div className="font-medium text-slate-700">Tavily</div>
              <div>
                {tavilyUsage.configured ? "已配置 Key" : "未配置 Key"}
                {" · "}
                调用 {tavilyUsage.total_queries} / token {tavilyUsage.total_tokens}
                {tavilyUsage.total_errors > 0 && (
                  <span className="text-amber-700">
                    {" "}
                    · 失败 {tavilyUsage.total_errors}
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
        <nav className="space-y-1 p-2">
          {navBtn("chat", "Chat", MessageSquare)}
          {navBtn("memory", "Memory", Database)}
          {navBtn("skills", "Skills", Sparkles)}
        </nav>
        <div className="min-h-0 flex-1 overflow-y-auto border-t border-slate-200 p-2">
          {nav === "chat" && (
            <div className="space-y-1">
              <div className="px-1 text-xs font-medium uppercase tracking-wide text-slate-400">
                历史会话
              </div>
              <button
                type="button"
                onClick={() => {
                  setSessionId("main_session");
                }}
                className={cn(
                  "w-full rounded-md px-2 py-1.5 text-left text-sm",
                  sessionId === "main_session"
                    ? "bg-slate-100 font-medium"
                    : "hover:bg-slate-50"
                )}
              >
                main_session
              </button>
              {sessions.map((s) => (
                <div key={s.session_id} className="flex flex-col gap-0.5">
                  <button
                    type="button"
                    onClick={() => setSessionId(s.session_id)}
                    className={cn(
                      "w-full rounded-md px-2 py-1.5 text-left text-sm",
                      sessionId === s.session_id
                        ? "bg-slate-100 font-medium"
                        : "hover:bg-slate-50"
                    )}
                  >
                    {s.session_id}
                  </button>
                  {s.path_md && (
                    <button
                      type="button"
                      className="pl-3 text-left text-xs text-slate-500 hover:text-slate-800"
                      onClick={() => openInEditor(s.path_md)}
                    >
                      打开 {s.path_md}
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
          {nav === "memory" && (
            <div className="space-y-1">
              <div className="px-1 text-xs font-medium uppercase tracking-wide text-slate-400">
                记忆文件
              </div>
              {memories.map((m) => (
                <div key={m.session_id} className="space-y-0.5">
                  {m.path_md && (
                    <button
                      type="button"
                      className="block w-full rounded px-2 py-1 text-left text-sm hover:bg-slate-100"
                      onClick={() => openInEditor(m.path_md)}
                    >
                      {m.path_md}
                    </button>
                  )}
                  {m.path_json && (
                    <button
                      type="button"
                      className="block w-full rounded px-2 py-1 text-left text-xs text-slate-500 hover:bg-slate-100"
                      onClick={() => openInEditor(m.path_json)}
                    >
                      {m.path_json}
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
          {nav === "skills" && (
            <div className="space-y-1">
              <div className="px-1 text-xs font-medium uppercase tracking-wide text-slate-400">
                技能
              </div>
              {skills.map((s) => (
                <button
                  key={s.path}
                  type="button"
                  className="block w-full rounded px-2 py-1.5 text-left text-sm hover:bg-slate-100"
                  onClick={() => openInEditor(s.path)}
                >
                  <div className="font-medium">{s.name}</div>
                  <div className="truncate text-xs text-slate-500">{s.path}</div>
                </button>
              ))}
            </div>
          )}
        </div>
      </aside>

      <main className="flex min-h-0 min-w-0 flex-1 flex-col border-r border-slate-200 bg-white">
        <header className="flex shrink-0 items-center justify-between border-b border-slate-200 px-4 py-2">
          <div className="text-sm text-slate-600">
            会话: <span className="font-mono text-slate-900">{sessionId}</span>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <label className="flex cursor-pointer items-center gap-1.5 text-slate-600">
              <input
                type="checkbox"
                checked={useStream}
                onChange={(e) => setUseStream(e.target.checked)}
              />
              SSE 流式
            </label>
            <button
              type="button"
              className="inline-flex items-center gap-1 rounded border border-slate-200 px-2 py-1 hover:bg-slate-50"
              onClick={() => {
                refreshSessions();
                refreshMemories();
                refreshSkills();
                void refreshUsage();
              }}
            >
              <RefreshCw className="h-3.5 w-3.5" />
              刷新
            </button>
          </div>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto p-4">
          <div className="mx-auto flex max-w-3xl flex-col gap-4">
            {messages.length === 0 && !streamingText && (
              <p className="text-center text-sm text-slate-400">
                向 AceClaw 发送消息；流式模式下可在下方「思考链」中查看 SSE 事件。
              </p>
            )}
            {messages.map((msg, i) => (
              <div
                key={i}
                className={cn(
                  "rounded-lg px-4 py-2 text-sm leading-relaxed",
                  msg.role === "user"
                    ? "ml-8 bg-slate-100 text-slate-900"
                    : "mr-8 border border-slate-200 bg-white text-slate-800"
                )}
              >
                <div className="mb-1 text-xs font-medium text-slate-400">
                  {msg.role === "user" ? "你" : "助手"}
                </div>
                <div className="whitespace-pre-wrap">{msg.content}</div>
              </div>
            ))}
            {streamingText && (
              <div className="mr-8 rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-2 text-sm text-slate-700">
                <div className="mb-1 text-xs font-medium text-slate-400">生成中…</div>
                <div className="whitespace-pre-wrap">{streamingText}</div>
              </div>
            )}
          </div>
        </div>

        <div className="shrink-0 border-t border-slate-200 px-4 py-2">
          <button
            type="button"
            className="flex w-full items-center gap-2 py-1 text-left text-xs font-medium text-slate-500 hover:text-slate-800"
            onClick={() => setThoughtsOpen((o) => !o)}
          >
            {thoughtsOpen ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
            思考链 / SSE 事件
          </button>
          {thoughtsOpen && (
            <pre className="mt-2 max-h-40 overflow-auto rounded bg-slate-900 p-2 font-mono text-[11px] text-slate-100">
              {thoughtLog.length === 0
                ? "（尚无事件）"
                : thoughtLog.join("\n")}
            </pre>
          )}
        </div>

        <footer className="shrink-0 border-t border-slate-200 p-4">
          <div className="mx-auto flex max-w-3xl gap-2">
            <input
              className="min-w-0 flex-1 rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-slate-400"
              placeholder="输入消息…"
              value={input}
              disabled={busy}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void sendChat();
                }
              }}
            />
            <button
              type="button"
              disabled={busy}
              className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              onClick={() => void sendChat()}
            >
              {busy ? "…" : "发送"}
            </button>
          </div>
        </footer>
      </main>

      <div className="flex h-full min-h-0 w-[min(42vw,560px)] shrink-0 flex-col bg-white">
        <div className="flex shrink-0 items-center justify-between gap-2 border-b border-slate-200 px-3 py-2">
          <span className="min-w-0 truncate font-mono text-xs text-slate-600" title={editorPath ?? ""}>
            {editorPath ?? "未选择文件"}
          </span>
          <button
            type="button"
            disabled={!editorPath || !editorDirty}
            className="inline-flex items-center gap-1 rounded border border-slate-200 px-2 py-1 text-xs disabled:opacity-40"
            onClick={() => void handleSaveEditor()}
          >
            <Save className="h-3.5 w-3.5" />
            保存
          </button>
        </div>
        <div className="min-h-0 flex-1">
          <MonacoEditorPanel
            path={editorPath}
            value={editorContent}
            onChange={(v) => {
              setEditorContent(v);
              setEditorDirty(true);
            }}
            className="h-full border-0"
          />
        </div>
      </div>
    </div>
  );
}
