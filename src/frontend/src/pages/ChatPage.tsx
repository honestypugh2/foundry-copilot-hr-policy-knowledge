import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import {
  sendMessage,
  type ChatMessage,
  type ChatResponse,
} from "../services/api";

interface MessageDisplay {
  role: "user" | "assistant";
  content: string;
  citations?: ChatResponse["citations"];
  policyReferences?: string[];
  glossaryMatches?: ChatResponse["glossary_matches"];
  confidence?: number;
  processingTime?: number;
}

const SUGGESTED_QUESTIONS = [
  "What is the PTO policy for full-time employees?",
  "What is the dress code policy?",
  "How does the probationary period work?",
  "What are the holiday pay rules?",
  "Tell me about the code of ethics.",
  "What is the short-term disability policy?",
];

export default function ChatPage() {
  const [messages, setMessages] = useState<MessageDisplay[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const conversationHistory: ChatMessage[] = messages.map((m) => ({
    role: m.role,
    content: m.content,
  }));

  async function handleSend(question?: string) {
    const q = (question ?? input).trim();
    if (!q || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: q }]);
    setLoading(true);

    try {
      const resp = await sendMessage(q, conversationHistory);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: resp.answer,
          citations: resp.citations,
          policyReferences: resp.policy_references,
          glossaryMatches: resp.glossary_matches,
          confidence: resp.confidence,
          processingTime: resp.processing_time_ms,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "Sorry, I encountered an error processing your question. Please try again.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto flex flex-col h-[calc(100vh-64px)]">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-16">
            <h2 className="text-2xl font-bold text-gray-700 mb-2">
              Welcome to Ask HR
            </h2>
            <p className="text-gray-500 mb-8">
              Ask any question about HR policies, benefits, leave, or
              workplace guidelines.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-2xl mx-auto">
              {SUGGESTED_QUESTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => handleSend(q)}
                  className="text-left p-3 bg-white border rounded-lg text-sm text-gray-700 hover:border-azure-500 hover:shadow transition-all"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${
              msg.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-5 py-3 ${
                msg.role === "user"
                  ? "bg-azure-600 text-white"
                  : "bg-white border shadow-sm"
              }`}
            >
              {msg.role === "assistant" ? (
                <div className="prose prose-sm max-w-none">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>
              ) : (
                <p>{msg.content}</p>
              )}

              {/* Glossary matches */}
              {msg.glossaryMatches && msg.glossaryMatches.length > 0 && (
                <div className="mt-3 p-2 bg-amber-50 border border-amber-200 rounded text-xs">
                  <span className="font-semibold text-amber-700">
                    Glossary:
                  </span>
                  {msg.glossaryMatches.map((g) => (
                    <span key={g.vernacular} className="ml-2 text-amber-800">
                      "{g.vernacular}" → {g.formal}
                    </span>
                  ))}
                </div>
              )}

              {/* Citations */}
              {msg.citations && msg.citations.length > 0 && (
                <div className="mt-3 border-t pt-2">
                  <p className="text-xs font-semibold text-gray-500 mb-1">
                    Sources:
                  </p>
                  {msg.citations.map((c, ci) => (
                    <div
                      key={ci}
                      className="text-xs text-gray-600 py-1 border-b last:border-0"
                    >
                      <span className="font-medium">
                        {c.title}
                      </span>
                      {c.policy_number && (
                        <span className="ml-1 text-azure-600">
                          (Policy {c.policy_number})
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Metadata */}
              {msg.role === "assistant" && msg.processingTime && (
                <div className="mt-2 flex gap-3 text-xs text-gray-400">
                  <span>{msg.processingTime}ms</span>
                  {msg.confidence !== undefined && (
                    <span>
                      Confidence: {Math.round(msg.confidence * 100)}%
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border rounded-2xl px-5 py-3 shadow-sm">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t bg-white p-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="max-w-3xl mx-auto flex gap-3"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about HR policies, benefits, leave, dress code…"
            className="flex-1 border rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-azure-500"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="bg-azure-600 text-white px-6 py-3 rounded-xl text-sm font-medium hover:bg-azure-700 disabled:opacity-50 transition-colors"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
