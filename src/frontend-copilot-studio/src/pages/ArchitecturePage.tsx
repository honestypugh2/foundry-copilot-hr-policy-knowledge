/**
 * Architecture page — visual overview of how Copilot Studio integrates with
 * Azure AI Search, Azure AI Foundry, and the HR policy knowledge base.
 */
export default function ArchitecturePage() {
  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <h2 className="text-2xl font-bold text-gray-800 mb-2">Architecture</h2>
      <p className="text-gray-500 text-sm mb-8">
        How the Copilot Studio HR Policy Agent connects to Azure services.
      </p>

      {/* Architecture Diagram (ASCII) */}
      <div className="bg-white border rounded-xl shadow-sm p-6 mb-8 overflow-x-auto">
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Integration Flow
        </h3>
        <pre className="text-xs font-mono text-gray-700 leading-relaxed">
{`┌─────────────────────────────────────────────────────────────────┐
│                        End Users                                │
│            (Teams, Web Chat, Custom Website)                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                   Microsoft Copilot Studio                       │
│                                                                  │
│  ┌──────────────┐   ┌────────────────┐   ┌───────────────────┐  │
│  │   Topics &   │   │   Knowledge    │   │    Actions &      │  │
│  │   Triggers   │   │   Sources      │   │    Connectors     │  │
│  └──────────────┘   └───────┬────────┘   └────────┬──────────┘  │
│                             │                      │             │
└─────────────────────────────┼──────────────────────┼─────────────┘
                              │                      │
              ┌───────────────┘                      └──────────┐
              ▼                                                  ▼
┌──────────────────────────┐               ┌──────────────────────────┐
│   Azure AI Search        │               │   Azure AI Foundry       │
│                          │               │                          │
│  ┌────────────────────┐  │               │  ┌────────────────────┐  │
│  │  hr-policy-index   │  │               │  │  HR Policy Agent   │  │
│  │                    │  │               │  │  (Agent Framework)  │  │
│  │  • Policy docs     │  │               │  │                    │  │
│  │  • Semantic search │  │               │  │  • Multi-step      │  │
│  │  • Vector + hybrid │  │               │  │  • Tool use        │  │
│  └────────────────────┘  │               │  │  • RAG pipeline    │  │
│                          │               │  └────────────────────┘  │
└──────────────────────────┘               └──────────────────────────┘
              ▲                                        ▲
              │                                        │
  ┌───────────┴────────────┐               ┌───────────┴──────────────┐
  │  Azure Document        │               │  Azure OpenAI Service    │
  │  Intelligence          │               │                          │
  │                        │               │  • GPT-4o               │
  │  • OCR for .doc/.docx  │               │  • Embeddings           │
  │  • Layout analysis     │               │  • Chat completions     │
  └────────────────────────┘               └──────────────────────────┘`}
        </pre>
      </div>

      {/* Component Details */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <Card
          icon="🔍"
          title="Azure AI Search"
          subtitle="Knowledge Source"
          color="azure"
        >
          <p>
            HR policy documents are indexed with semantic and vector search
            capabilities. Copilot Studio queries this index as its primary
            knowledge source, returning grounded answers with policy citations.
          </p>
          <ul className="mt-2 space-y-1">
            <li>Hybrid search (keyword + semantic)</li>
            <li>Connected via Power Platform connector</li>
            <li>Index: <code>hr-policy-index</code></li>
          </ul>
        </Card>

        <Card
          icon="🤖"
          title="Azure AI Foundry"
          subtitle="Agent Integration"
          color="copilot"
        >
          <p>
            An advanced HR policy agent built with Azure AI Agent Framework. Copilot
            Studio delegates complex multi-step tasks to this agent for deeper
            analysis and tool-augmented reasoning.
          </p>
          <ul className="mt-2 space-y-1">
            <li>Multi-turn reasoning</li>
            <li>Connected as an Action in Copilot Studio</li>
            <li>Orchestrated via Agent Framework</li>
          </ul>
        </Card>

        <Card
          icon="📄"
          title="Document Intelligence"
          subtitle="Document Processing"
          color="azure"
        >
          <p>
            Extracts text content from HR policy documents (.docx, .doc, .pdf)
            using Azure Document Intelligence. Extracted content is chunked
            and indexed in AI Search.
          </p>
          <ul className="mt-2 space-y-1">
            <li>OCR for scanned documents</li>
            <li>Layout and structure extraction</li>
            <li>Automated pipeline via ingestion scripts</li>
          </ul>
        </Card>

        <Card
          icon="💬"
          title="Copilot Studio"
          subtitle="Agent Orchestration"
          color="copilot"
        >
          <p>
            Microsoft Copilot Studio provides the conversational AI layer with
            built-in topic management, authentication, and multi-channel
            deployment (Teams, Web, Custom).
          </p>
          <ul className="mt-2 space-y-1">
            <li>Low-code agent builder</li>
            <li>Direct Line token for web embed</li>
            <li>Generative AI with knowledge grounding</li>
          </ul>
        </Card>
      </div>

      {/* Data Flow */}
      <div className="bg-white border rounded-xl shadow-sm p-6">
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Query Flow
        </h3>
        <ol className="space-y-3 text-sm text-gray-700">
          <Step n={1}>
            User sends a question through the Web Chat widget (this frontend)
            or Microsoft Teams.
          </Step>
          <Step n={2}>
            Copilot Studio receives the message and identifies intent using
            its topic model and generative orchestration.
          </Step>
          <Step n={3}>
            For HR policy questions, Copilot Studio queries{" "}
            <strong>Azure AI Search</strong> to find relevant policy documents.
          </Step>
          <Step n={4}>
            If the question requires complex analysis, Copilot Studio delegates
            to the <strong>Azure AI Foundry agent</strong> as an action.
          </Step>
          <Step n={5}>
            The response is composed with citations and policy references, then
            returned to the user.
          </Step>
        </ol>
      </div>
    </div>
  );
}

/* -- Helper components -- */

function Card({
  icon,
  title,
  subtitle,
  color,
  children,
}: {
  icon: string;
  title: string;
  subtitle: string;
  color: "azure" | "copilot";
  children: React.ReactNode;
}) {
  const borderColor =
    color === "azure" ? "border-azure-200" : "border-copilot-200";
  const tagBg =
    color === "azure"
      ? "bg-azure-100 text-azure-700"
      : "bg-copilot-100 text-copilot-700";

  return (
    <div className={`bg-white border ${borderColor} rounded-xl p-5`}>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xl">{icon}</span>
        <div>
          <h4 className="font-semibold text-gray-800 text-sm">{title}</h4>
          <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${tagBg}`}>
            {subtitle}
          </span>
        </div>
      </div>
      <div className="text-xs text-gray-600 leading-relaxed [&_li]:before:content-['•'] [&_li]:before:mr-1.5 [&_li]:before:text-gray-400">
        {children}
      </div>
    </div>
  );
}

function Step({ n, children }: { n: number; children: React.ReactNode }) {
  return (
    <li className="flex gap-3">
      <span className="flex-shrink-0 flex items-center justify-center w-6 h-6 rounded-full bg-copilot-600 text-white text-xs font-bold">
        {n}
      </span>
      <span>{children}</span>
    </li>
  );
}
