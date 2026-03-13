import { useEffect, useState } from "react";
import { getHealth, type HealthResponse } from "../services/api";

export default function AboutPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    getHealth().then(setHealth).catch(console.error);
  }, []);

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-8">
      <h2 className="text-2xl font-bold text-gray-800">
        About Ask HR Knowledge Agent
      </h2>

      {/* Overview */}
      <section className="bg-white border rounded-lg p-6 space-y-3">
        <h3 className="font-semibold text-lg text-gray-700">Overview</h3>
        <p className="text-sm text-gray-600 leading-relaxed">
          This demo showcases an AI-powered HR policy assistant built with
          Azure AI Foundry, Azure AI Search, Azure Document Intelligence, and
          the Microsoft Agent Framework. It answers employee questions by
          retrieving and reasoning over internal HR policy documents.
        </p>
      </section>

      {/* Architecture */}
      <section className="bg-white border rounded-lg p-6 space-y-3">
        <h3 className="font-semibold text-lg text-gray-700">Architecture</h3>
        <div className="text-sm text-gray-600 space-y-2">
          <p>
            <strong>Document Ingestion:</strong> Word documents are processed
            using Azure Document Intelligence (or python-docx fallback) and
            indexed into Azure AI Search.
          </p>
          <p>
            <strong>Sequential Workflow:</strong> When a question is asked, the
            Agent Framework orchestrates three steps: Query Understanding
            (glossary expansion), Policy Retrieval (AI Search), and Answer
            Generation (RAG with citations).
          </p>
          <p>
            <strong>Vernacular Mapping:</strong> An HR glossary maps informal
            terms (e.g., &quot;PTO&quot;, &quot;dress code&quot;) to formal
            policy names for better search accuracy.
          </p>
        </div>
      </section>

      {/* Challenges addressed */}
      <section className="bg-white border rounded-lg p-6 space-y-3">
        <h3 className="font-semibold text-lg text-gray-700">
          Challenges Addressed
        </h3>
        <ol className="list-decimal list-inside text-sm text-gray-600 space-y-2">
          <li>
            <strong>Incorrect grounding</strong> — Answers cite specific policy
            numbers and are restricted to retrieved documents only.
          </li>
          <li>
            <strong>Vernacular difficulty</strong> — HR glossary expands
            shorthand into formal policy terms before search.
          </li>
          <li>
            <strong>Multiple data sources</strong> — Sub-agent pattern handles
            different policy categories independently.
          </li>
          <li>
            <strong>Prompt limitations</strong> — Detailed agent instructions
            with strict grounding rules replace basic prompting.
          </li>
        </ol>
      </section>

      {/* Azure service health */}
      <section className="bg-white border rounded-lg p-6 space-y-3">
        <h3 className="font-semibold text-lg text-gray-700">
          Azure Service Status
        </h3>
        {health ? (
          <div className="space-y-2">
            <div className="flex items-center gap-2 mb-3">
              <span
                className={`w-3 h-3 rounded-full ${
                  health.status === "healthy"
                    ? "bg-green-500"
                    : "bg-yellow-500"
                }`}
              />
              <span className="text-sm font-medium capitalize">
                {health.status}
              </span>
            </div>
            {Object.entries(health.services).map(([key, svc]) => (
              <div
                key={key}
                className="flex items-center justify-between border-b py-2 text-sm"
              >
                <span className="text-gray-700">{svc.name}</span>
                <div className="flex items-center gap-2">
                  <span
                    className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      svc.status === "healthy" || svc.status === "available"
                        ? "bg-green-100 text-green-700"
                        : svc.status === "configured"
                        ? "bg-blue-100 text-blue-700"
                        : "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {svc.status}
                  </span>
                  {svc.details && (
                    <span className="text-gray-400">{svc.details}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-400">Loading…</p>
        )}
      </section>

      {/* Tech stack */}
      <section className="bg-white border rounded-lg p-6 space-y-3">
        <h3 className="font-semibold text-lg text-gray-700">Tech Stack</h3>
        <div className="grid grid-cols-2 gap-2 text-sm text-gray-600">
          <span>Azure AI Foundry (azure-ai-projects)</span>
          <span>Microsoft Agent Framework</span>
          <span>Azure AI Search</span>
          <span>Azure Document Intelligence</span>
          <span>Azure OpenAI</span>
          <span>Copilot Studio</span>
          <span>FastAPI + Uvicorn</span>
          <span>React + TypeScript + Vite</span>
        </div>
      </section>
    </div>
  );
}
