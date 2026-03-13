import axios from "axios";

const api = axios.create({ baseURL: "/api" });

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
  total_indexed: number;
  local_files_count: number;
  local_files: string[];
  index_name: string;
}

export interface HealthResponse {
  status: string;
  services: Record<
    string,
    { name: string; status: string; details?: string }
  >;
}

export interface GlossaryEntry {
  vernacular: string;
  formal: string;
}

export async function sendMessage(
  question: string,
  conversationHistory: ChatMessage[]
): Promise<ChatResponse> {
  const { data } = await api.post<ChatResponse>("/chat", {
    question,
    conversation_history: conversationHistory,
  });
  return data;
}

export async function getKnowledgeBaseInfo(): Promise<KnowledgeBaseInfo> {
  const { data } = await api.get<KnowledgeBaseInfo>("/knowledge-base");
  return data;
}

export async function getHealth(): Promise<HealthResponse> {
  const { data } = await api.get<HealthResponse>("/health");
  return data;
}

export async function getGlossary(): Promise<{
  glossary: GlossaryEntry[];
  total: number;
}> {
  const { data } = await api.get("/glossary");
  return data;
}

export async function reindexKnowledgeBase(): Promise<Record<string, unknown>> {
  const { data } = await api.post("/knowledge-base/reindex");
  return data;
}
