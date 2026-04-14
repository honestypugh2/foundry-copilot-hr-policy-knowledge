const BASE_URL = "/api";

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, init);
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  answer: string;
  citations: Array<{
    title: string;
    policy_number: string;
    excerpt: string;
  }>;
  policy_references: string[];
  confidence: number;
  glossary_matches: Array<{
    vernacular: string;
    formal: string;
  }>;
  processing_time_ms: number;
}

export interface KnowledgeBaseInfo {
  total_documents: number;
  categories: Record<string, number>;
  documents: Array<{ name: string }>;
  index_status: string;
}

export interface ServiceStatus {
  name: string;
  status: string;
  details?: string;
}

export interface HealthResponse {
  status: string;
  message: string;
  version: string;
  services: Record<string, ServiceStatus>;
}

export interface GlossaryEntry {
  vernacular: string;
  formal: string;
}

export async function sendMessage(
  question: string,
  conversationHistory: ChatMessage[]
): Promise<ChatResponse> {
  return fetchJson<ChatResponse>("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message: question,
      conversation_history: conversationHistory,
    }),
  });
}

export async function getKnowledgeBaseInfo(): Promise<KnowledgeBaseInfo> {
  return fetchJson<KnowledgeBaseInfo>("/knowledge-base");
}

export async function getHealth(): Promise<HealthResponse> {
  return fetchJson<HealthResponse>("/health");
}

export async function getGlossary(): Promise<{
  glossary: GlossaryEntry[];
  total: number;
}> {
  return fetchJson("/glossary");
}

export async function reindexKnowledgeBase(): Promise<Record<string, unknown>> {
  return fetchJson("/knowledge-base/reindex", { method: "POST" });
}
