/**
 * Setup Guide — step-by-step instructions for configuring the Copilot Studio
 * agent with Azure AI Search knowledge and Azure AI Foundry agent integration.
 */
export default function SetupGuidePage() {
  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <h2 className="text-2xl font-bold text-gray-800 mb-2">Setup Guide</h2>
      <p className="text-gray-500 text-sm mb-8">
        Follow these steps to configure your Copilot Studio HR Policy agent
        with Azure AI Search knowledge and Azure AI Foundry integration.
      </p>

      {/* Prerequisites */}
      <Section number={0} title="Prerequisites">
        <ul className="list-disc list-inside text-sm text-gray-700 space-y-1.5">
          <li>
            Azure subscription with Azure AI Search, Azure AI Foundry, and Azure
            Document Intelligence deployed
          </li>
          <li>
            Power Platform environment with Copilot Studio license (trial or
            paid)
          </li>
          <li>
            HR policy documents indexed in Azure AI Search (use the{" "}
            <code className="bg-gray-100 px-1 rounded text-xs font-mono">
              scripts/index_knowledge_base.py
            </code>{" "}
            script)
          </li>
        </ul>
      </Section>

      {/* Step 1 */}
      <Section number={1} title="Create a Copilot Studio Agent">
        <ol className="list-decimal list-inside text-sm text-gray-700 space-y-2">
          <li>
            Go to{" "}
            <ExternalLink href="https://copilotstudio.microsoft.com">
              copilotstudio.microsoft.com
            </ExternalLink>
          </li>
          <li>
            Click <strong>Create</strong> → <strong>New agent</strong>
          </li>
          <li>
            Name the agent <strong>Ask HR Policy Agent</strong>
          </li>
          <li>
            Set the description:{" "}
            <em>
              "Answers employee questions about HR policies, benefits, leave,
              hiring, and workplace procedures."
            </em>
          </li>
          <li>
            Set the instructions:{" "}
            <em>
              "You are an HR policy assistant. Answer questions using only the
              provided knowledge sources. Cite the specific policy number and
              title when possible. If you are unsure, say so and recommend the
              employee contact HR directly."
            </em>
          </li>
          <li>
            Click <strong>Create</strong>
          </li>
        </ol>
      </Section>

      {/* Step 2 */}
      <Section number={2} title="Add Azure AI Search Knowledge Source">
        <p className="text-sm text-gray-600 mb-3">
          Connect your indexed HR policy documents as a knowledge source.
        </p>
        <ol className="list-decimal list-inside text-sm text-gray-700 space-y-2">
          <li>
            In your agent, go to <strong>Knowledge</strong> →{" "}
            <strong>Add knowledge</strong>
          </li>
          <li>
            Select <strong>Azure AI Search</strong>
          </li>
          <li>
            Enter your Azure AI Search endpoint URL (from{" "}
            <code className="bg-gray-100 px-1 rounded text-xs font-mono">
              AZURE_AI_SEARCH_ENDPOINT
            </code>{" "}
            in .env)
          </li>
          <li>
            Select your index:{" "}
            <code className="bg-gray-100 px-1 rounded text-xs font-mono">
              hr-policy-index
            </code>
          </li>
          <li>
            Provide the API key or configure managed identity authentication
          </li>
          <li>
            Map the fields:
            <ul className="list-disc list-inside ml-5 mt-1 space-y-1">
              <li>
                <strong>Content field</strong> → <code className="text-xs font-mono">content</code>
              </li>
              <li>
                <strong>Title field</strong> → <code className="text-xs font-mono">title</code>
              </li>
              <li>
                <strong>URL field</strong> → <code className="text-xs font-mono">source_url</code>{" "}
                (optional)
              </li>
            </ul>
          </li>
          <li>
            Click <strong>Add</strong>
          </li>
        </ol>
        <InfoBox>
          Alternatively, create a custom connector in Power Platform to call the
          Azure AI Search REST API. See the{" "}
          <ExternalLink href="https://learn.microsoft.com/en-us/microsoft-copilot-studio/knowledge-azure-ai-search">
            Azure AI Search knowledge docs
          </ExternalLink>
          .
        </InfoBox>
      </Section>

      {/* Step 3 */}
      <Section number={3} title="Add Azure AI Foundry Agent (Optional)">
        <p className="text-sm text-gray-600 mb-3">
          Extend your Copilot Studio agent with an Azure AI Foundry agent for
          advanced reasoning, multi-step analysis, or custom tool use.
        </p>
        <ol className="list-decimal list-inside text-sm text-gray-700 space-y-2">
          <li>
            In your agent, go to <strong>Actions</strong> →{" "}
            <strong>Add an action</strong>
          </li>
          <li>
            Select <strong>Azure AI Foundry agent</strong>
          </li>
          <li>
            Sign in to your Azure account if prompted
          </li>
          <li>
            Select the AI Foundry project containing your HR agent
          </li>
          <li>
            Choose the agent and configure input/output mappings
          </li>
          <li>
            Click <strong>Add</strong>
          </li>
        </ol>
        <InfoBox>
          The Foundry agent runs as a sub-agent, meaning Copilot Studio will
          delegate specific tasks to it. See the{" "}
          <ExternalLink href="https://learn.microsoft.com/en-us/microsoft-copilot-studio/add-agent-foundry-agent">
            Foundry agent integration docs
          </ExternalLink>
          .
        </InfoBox>
      </Section>

      {/* Step 4 */}
      <Section number={4} title="Publish and Get Embed Settings">
        <ol className="list-decimal list-inside text-sm text-gray-700 space-y-2">
          <li>
            Click <strong>Publish</strong> in the top right of Copilot Studio
          </li>
          <li>
            Go to <strong>Settings</strong> → <strong>Channels</strong> →{" "}
            <strong>Custom website</strong>
          </li>
          <li>
            Copy the <strong>Token endpoint</strong> URL — this is your{" "}
            <code className="bg-gray-100 px-1 rounded text-xs font-mono">
              COPILOT_STUDIO_TOKEN_ENDPOINT
            </code>
          </li>
          <li>
            Note the environment ID and agent schema name from the URL
          </li>
        </ol>
      </Section>

      {/* Step 5 */}
      <Section number={5} title="Configure Environment Variables">
        <p className="text-sm text-gray-600 mb-3">
          Add the following to your{" "}
          <code className="bg-gray-100 px-1 rounded text-xs font-mono">
            .env
          </code>{" "}
          file:
        </p>
        <pre className="bg-gray-900 text-gray-100 rounded-lg p-4 text-xs font-mono overflow-x-auto">
{`# Copilot Studio
COPILOT_STUDIO_ENVIRONMENT_ID=9cb938ce-b109-e86f-99ee-7bad48b89f09
COPILOT_STUDIO_AGENT_SCHEMA=cr4ba_askHrPolicyAgent
COPILOT_STUDIO_REGION=unitedstates

# Or use the full token endpoint URL directly:
# COPILOT_STUDIO_TOKEN_ENDPOINT=https://default...environment.api.powerplatform.com/powervirtualagents/botsbyschema/.../directline/token`}
        </pre>
        <p className="text-gray-500 text-xs mt-2">
          Restart the backend after updating .env.
        </p>
      </Section>

      {/* Step 6 */}
      <Section number={6} title="Test the Integration">
        <ol className="list-decimal list-inside text-sm text-gray-700 space-y-2">
          <li>
            Start the backend:{" "}
            <code className="bg-gray-100 px-1 rounded text-xs font-mono">
              python -m src.backend.main
            </code>
          </li>
          <li>
            Start this frontend:{" "}
            <code className="bg-gray-100 px-1 rounded text-xs font-mono">
              cd src/frontend-copilot-studio && npm run dev
            </code>
          </li>
          <li>
            Open{" "}
            <ExternalLink href="http://localhost:5174">
              http://localhost:5174
            </ExternalLink>
          </li>
          <li>
            Try asking: <em>"What is the PTO policy?"</em> or{" "}
            <em>"How does the probationary period work?"</em>
          </li>
        </ol>
      </Section>
    </div>
  );
}

/* -- Helper components -- */

function Section({
  number,
  title,
  children,
}: {
  number: number;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mb-8">
      <h3 className="flex items-center gap-2 text-lg font-semibold text-gray-800 mb-3">
        <span className="flex items-center justify-center w-7 h-7 rounded-full bg-copilot-600 text-white text-xs font-bold">
          {number}
        </span>
        {title}
      </h3>
      <div className="pl-9">{children}</div>
    </section>
  );
}

function InfoBox({ children }: { children: React.ReactNode }) {
  return (
    <div className="mt-3 bg-azure-50 border border-azure-200 rounded-lg p-3 text-sm text-azure-700">
      {children}
    </div>
  );
}

function ExternalLink({
  href,
  children,
}: {
  href: string;
  children: React.ReactNode;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-azure-600 underline hover:text-azure-700"
    >
      {children}
    </a>
  );
}
