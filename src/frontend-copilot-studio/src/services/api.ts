import axios from "axios";

const api = axios.create({ baseURL: "/api" });

/** Fetch a Direct Line token for the Copilot Studio Web Chat embed. */
export async function getCopilotStudioToken(): Promise<{
  token: string;
  conversationId?: string;
}> {
  const { data } = await api.get("/copilot-studio/token");
  return data;
}

/** Get safe-to-expose Copilot Studio configuration. */
export async function getCopilotStudioConfig(): Promise<{
  configured: boolean;
  environment_id?: string;
  region?: string;
}> {
  const { data } = await api.get("/copilot-studio/config");
  return data;
}

/** Send a message through the backend proxy to Copilot Studio. */
export async function sendCopilotStudioMessage(question: string): Promise<{
  answer: string;
  source: string;
  conversation_id: string;
  processing_time_ms: number;
}> {
  const { data } = await api.post("/copilot-studio/chat", { message: question });
  return data;
}

/** Health check for all backend services. */
export async function getHealth(): Promise<Record<string, unknown>> {
  const { data } = await api.get("/health");
  return data;
}

/** Azure service status. */
export async function getAzureStatus(): Promise<Record<string, unknown>> {
  const { data } = await api.get("/azure/status");
  return data;
}
