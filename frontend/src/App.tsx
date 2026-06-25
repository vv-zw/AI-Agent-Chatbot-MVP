import { FormEvent, useCallback, useEffect, useState } from "react";

import { api } from "./lib/api";
import type { ChatMessage, ChatSession, ToolCall } from "./types/api";

function messageStyle(role: ChatMessage["role"]) {
  if (role === "user") {
    return "ml-auto bg-brand text-white";
  }
  if (role === "tool") {
    return "mr-auto border border-amber-200 bg-amber-50 text-amber-950";
  }
  return "mr-auto border border-slate-200 bg-white text-ink";
}

export default function App() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSession = useCallback(async (sessionId: string) => {
    setError(null);
    const detail = await api.getSession(sessionId);
    setActiveSessionId(sessionId);
    setMessages(detail.messages);
    setToolCalls(detail.tool_calls);
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        const items = await api.listSessions();
        setSessions(items);
        if (items[0]) {
          await loadSession(items[0].id);
        }
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Failed to load.");
      }
    })();
  }, [loadSession]);

  async function createSession() {
    if (isSending) return;
    try {
      setError(null);
      const created = await api.createSession();
      setSessions((current) => [created, ...current]);
      setActiveSessionId(created.id);
      setMessages([]);
      setToolCalls([]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to create.");
    }
  }

  async function sendMessage(event: FormEvent) {
    event.preventDefault();
    const content = input.trim();
    if (!content || !activeSessionId || isSending) return;

    try {
      setIsSending(true);
      setError(null);
      const result = await api.sendMessage(activeSessionId, { content });
      setInput("");
      setMessages((current) => [
        ...current,
        result.user_message,
        result.assistant_message,
      ]);
      setToolCalls((current) => [...current, ...result.tool_calls]);
      const refreshed = await api.listSessions();
      setSessions(refreshed);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to send.");
    } finally {
      setIsSending(false);
    }
  }

  return (
    <main className="min-h-screen bg-canvas text-ink">
      <div className="mx-auto grid min-h-screen max-w-7xl md:grid-cols-[280px_1fr]">
        <aside className="border-r border-slate-200 bg-slate-950 p-5 text-white">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-violet-300">
                Local-first
              </p>
              <h1 className="mt-1 text-lg font-semibold">Agent Chatbot</h1>
            </div>
            <span className="rounded-full bg-emerald-400/15 px-2 py-1 text-xs text-emerald-300">
              Mock
            </span>
          </div>

          <button
            className="mb-5 w-full rounded-xl bg-white px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-violet-100 disabled:opacity-50"
            onClick={() => void createSession()}
            disabled={isSending}
          >
            + New conversation
          </button>

          <nav className="space-y-2">
            {sessions.map((session) => (
              <button
                key={session.id}
                className={`w-full rounded-xl px-3 py-3 text-left text-sm transition ${
                  activeSessionId === session.id
                    ? "bg-violet-500 text-white"
                    : "text-slate-300 hover:bg-slate-800"
                }`}
                onClick={() => void loadSession(session.id)}
              >
                <span className="block truncate">{session.title}</span>
              </button>
            ))}
            {sessions.length === 0 && (
              <p className="px-2 text-sm text-slate-500">No conversations yet.</p>
            )}
          </nav>
        </aside>

        <section className="flex min-h-screen flex-col">
          <header className="border-b border-slate-200 bg-white px-6 py-4">
            <h2 className="font-semibold">
              {activeSessionId ? "Conversation" : "Start a conversation"}
            </h2>
            <p className="text-sm text-slate-500">
              Messages and tool traces are persisted by FastAPI + SQLite.
            </p>
          </header>

          <div className="flex-1 space-y-4 overflow-y-auto p-6">
            {messages.length === 0 && (
              <div className="mx-auto mt-20 max-w-md text-center">
                <div className="mx-auto mb-4 grid size-14 place-items-center rounded-2xl bg-violet-100 text-2xl">
                  ✦
                </div>
                <h3 className="text-xl font-semibold">A clean starting point</h3>
                <p className="mt-2 text-sm leading-6 text-slate-500">
                  Create a conversation, then send a message. Tool execution
                  cards will appear here in the next implementation stage.
                </p>
              </div>
            )}

            {messages.map((message) => (
              <article
                key={message.id}
                className={`max-w-2xl rounded-2xl px-4 py-3 shadow-sm ${messageStyle(
                  message.role,
                )}`}
              >
                <p className="mb-1 text-xs font-semibold uppercase opacity-60">
                  {message.role}
                </p>
                <p className="whitespace-pre-wrap text-sm leading-6">
                  {message.content}
                </p>
              </article>
            ))}

            {toolCalls.map((call) => (
              <article
                key={call.id}
                className="max-w-2xl rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm"
              >
                <p className="font-semibold">Tool · {call.tool_name}</p>
                <p className="mt-1 text-amber-800">Status: {call.status}</p>
              </article>
            ))}

            {isSending && (
              <div className="mr-auto rounded-2xl border bg-white px-4 py-3 text-sm text-slate-500">
                Assistant is thinking…
              </div>
            )}
          </div>

          <footer className="border-t border-slate-200 bg-white p-5">
            {error && (
              <p className="mx-auto mb-3 max-w-3xl rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
                {error}
              </p>
            )}
            <form
              className="mx-auto flex max-w-3xl gap-3"
              onSubmit={(event) => void sendMessage(event)}
            >
              <input
                className="min-w-0 flex-1 rounded-xl border border-slate-300 px-4 py-3 outline-none transition focus:border-brand focus:ring-2 focus:ring-violet-100 disabled:bg-slate-100"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder={
                  activeSessionId
                    ? "Ask something…"
                    : "Create a conversation first"
                }
                disabled={!activeSessionId || isSending}
              />
              <button
                className="rounded-xl bg-brand px-5 py-3 font-semibold text-white transition hover:bg-violet-700 disabled:cursor-not-allowed disabled:opacity-40"
                disabled={!activeSessionId || !input.trim() || isSending}
                type="submit"
              >
                Send
              </button>
            </form>
          </footer>
        </section>
      </div>
    </main>
  );
}

