const BASE_URL = "/api";

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, init);
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

/** Fetch a Direct Line token for the Copilot Studio Web Chat embed. */
export async function getCopilotStudioToken(): Promise<{
  token: string;
  conversationId?: string;
}> {
  return fetchJson("/copilot-studio/token");
}

/** Get safe-to-expose Copilot Studio configuration. */
export async function getCopilotStudioConfig(): Promise<{
  configured: boolean;
  environment_id?: string;
  region?: string;
}> {
  return fetchJson("/copilot-studio/config");
}

/** Send a message through the backend proxy to Copilot Studio. */
export async function sendCopilotStudioMessage(question: string): Promise<{
  answer: string;
  source: string;
  conversation_id: string;
  processing_time_ms: number;
}> {
  return fetchJson("/copilot-studio/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: question }),
  });
}

/** Health check for all backend services. */
export async function getHealth(): Promise<Record<string, unknown>> {
  return fetchJson("/health");
}

/** Azure service status. */
export async function getAzureStatus(): Promise<Record<string, unknown>> {
  return fetchJson("/azure/status");
}
