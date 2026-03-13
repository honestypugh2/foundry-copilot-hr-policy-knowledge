import { useState, useEffect, useCallback, useRef } from "react";
import ReactWebChat, { createDirectLine } from "botframework-webchat";
import {
  getCopilotStudioToken,
  getCopilotStudioConfig,
  sendCopilotStudioMessage,
} from "../services/api";

type Mode = "embed" | "proxy";

interface ProxyMessage {
  role: "user" | "assistant";
  content: string;
}

/**
 * Chat page with two modes:
 * 1. **Embed** — Bot Framework Web Chat widget connected via Direct Line token
 * 2. **Proxy** — Simple chat UI that proxies messages through the FastAPI backend
 */
export default function ChatPage() {
  const [mode, setMode] = useState<Mode>("embed");
  const [configured, setConfigured] = useState<boolean | null>(null);

  useEffect(() => {
    getCopilotStudioConfig()
      .then((c) => setConfigured(c.configured))
      .catch(() => setConfigured(false));
  }, []);

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">
            Copilot Studio Chat
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            Ask HR policy questions powered by Microsoft Copilot Studio with
            Azure AI Search knowledge.
          </p>
        </div>

        {/* Mode toggle */}
        <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
          <button
            onClick={() => setMode("embed")}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              mode === "embed"
                ? "bg-white text-copilot-700 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            Web Chat Embed
          </button>
          <button
            onClick={() => setMode("proxy")}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              mode === "proxy"
                ? "bg-white text-copilot-700 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            Backend Proxy
          </button>
        </div>
      </div>

      {configured === null && (
        <div className="flex items-center gap-2 text-gray-500">
          <span className="animate-spin">⏳</span> Checking Copilot Studio
          configuration…
        </div>
      )}

      {configured === false && <NotConfiguredBanner />}

      {configured && mode === "embed" && <WebChatEmbed />}
      {configured && mode === "proxy" && <ProxyChat />}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/*  Web Chat Embed Mode                                                       */
/* -------------------------------------------------------------------------- */

function WebChatEmbed() {
  const [directLine, setDirectLine] = useState<ReturnType<
    typeof createDirectLine
  > | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    getCopilotStudioToken()
      .then(({ token }) => {
        if (cancelled) return;
        setDirectLine(createDirectLine({ token }));
      })
      .catch((err) => {
        if (cancelled) return;
        setError(
          err?.response?.data?.detail ??
            "Failed to get Direct Line token. Check backend logs."
        );
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">
        <strong>Error:</strong> {error}
      </div>
    );
  }

  if (!directLine) {
    return (
      <div className="flex items-center gap-2 text-gray-500 py-12 justify-center">
        <span className="animate-spin">⏳</span> Connecting to Copilot
        Studio…
      </div>
    );
  }

  return (
    <div className="border rounded-xl overflow-hidden shadow-lg bg-white h-[600px]">
      <ReactWebChat
        directLine={directLine}
        styleOptions={{
          rootHeight: "100%",
          rootWidth: "100%",
          bubbleBackground: "#f0fdf4",
          bubbleFromUserBackground: "#eff6ff",
          sendBoxButtonColor: "#16a34a",
          primaryFont: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
        }}
      />
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/*  Proxy Chat Mode                                                           */
/* -------------------------------------------------------------------------- */

function ProxyChat() {
  const [messages, setMessages] = useState<ProxyMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = useCallback(async () => {
    const question = input.trim();
    if (!question || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setLoading(true);

    try {
      const result = await sendCopilotStudioMessage(question);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: result.answer },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, I encountered an error. Please try again.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }, [input, loading]);

  return (
    <div className="border rounded-xl bg-white shadow-lg flex flex-col h-[600px]">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="text-center text-gray-400 py-20">
            Ask an HR policy question to get started.
          </div>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[75%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
                m.role === "user"
                  ? "bg-azure-100 text-azure-700"
                  : "bg-copilot-50 text-gray-800 border border-copilot-100"
              }`}
            >
              {m.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-copilot-50 border border-copilot-100 px-4 py-2.5 rounded-2xl text-sm text-gray-500 animate-pulse">
              Thinking…
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t p-3 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Ask an HR policy question…"
          className="flex-1 px-4 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-copilot-500"
          disabled={loading}
        />
        <button
          onClick={send}
          disabled={loading || !input.trim()}
          className="px-5 py-2 bg-copilot-600 text-white rounded-lg text-sm font-medium hover:bg-copilot-700 disabled:opacity-50 transition-colors"
        >
          Send
        </button>
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/*  Not Configured Banner                                                     */
/* -------------------------------------------------------------------------- */

function NotConfiguredBanner() {
  return (
    <div className="bg-amber-50 border border-amber-200 rounded-lg p-6">
      <h3 className="text-amber-800 font-semibold text-base mb-2">
        Copilot Studio Not Configured
      </h3>
      <p className="text-amber-700 text-sm mb-3">
        Set the following environment variables in your{" "}
        <code className="bg-amber-100 px-1.5 py-0.5 rounded text-xs font-mono">
          .env
        </code>{" "}
        file and restart the backend:
      </p>
      <ul className="text-amber-700 text-sm space-y-1 list-disc list-inside">
        <li>
          <code className="font-mono text-xs">COPILOT_STUDIO_ENVIRONMENT_ID</code>{" "}
          — Power Platform environment ID
        </li>
        <li>
          <code className="font-mono text-xs">COPILOT_STUDIO_AGENT_SCHEMA</code>{" "}
          — Agent schema name (e.g. cr4ba_askHrPolicyAgent)
        </li>
        <li>
          <code className="font-mono text-xs">COPILOT_STUDIO_REGION</code>{" "}
          — Region (default: unitedstates)
        </li>
      </ul>
      <p className="text-amber-600 text-xs mt-3">
        See the <strong>Setup Guide</strong> tab for step-by-step instructions.
      </p>
    </div>
  );
}
