import { useEffect, useState } from "react";
import {
  getKnowledgeBaseInfo,
  getGlossary,
  reindexKnowledgeBase,
  type KnowledgeBaseInfo,
  type GlossaryEntry,
} from "../services/api";

export default function KnowledgeBasePage() {
  const [info, setInfo] = useState<KnowledgeBaseInfo | null>(null);
  const [glossary, setGlossary] = useState<GlossaryEntry[]>([]);
  const [reindexing, setReindexing] = useState(false);
  const [reindexResult, setReindexResult] = useState<string | null>(null);

  useEffect(() => {
    getKnowledgeBaseInfo().then(setInfo).catch(console.error);
    getGlossary()
      .then((d) => setGlossary(d.glossary))
      .catch(console.error);
  }, []);

  async function handleReindex() {
    setReindexing(true);
    setReindexResult(null);
    try {
      const res = await reindexKnowledgeBase();
      setReindexResult(
        `Indexed ${res.processed ?? 0}/${res.total_files ?? 0} documents. ${res.failed ?? 0} failed.`
      );
      getKnowledgeBaseInfo().then(setInfo);
    } catch {
      setReindexResult("Re-indexing failed. Check server logs.");
    } finally {
      setReindexing(false);
    }
  }

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-8">
      <h2 className="text-2xl font-bold text-gray-800">Knowledge Base</h2>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          label="Indexed Documents"
          value={info?.total_indexed ?? "—"}
        />
        <StatCard
          label="Local Files"
          value={info?.local_files_count ?? "—"}
        />
        <StatCard label="Index Name" value={info?.index_name ?? "—"} />
      </div>

      {/* Re-index */}
      <div className="bg-white border rounded-lg p-5">
        <h3 className="font-semibold text-gray-700 mb-2">
          Re-index Knowledge Base
        </h3>
        <p className="text-sm text-gray-500 mb-3">
          Process all Word documents and update the Azure AI Search index.
        </p>
        <button
          onClick={handleReindex}
          disabled={reindexing}
          className="bg-azure-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-azure-700 disabled:opacity-50"
        >
          {reindexing ? "Indexing…" : "Re-index Now"}
        </button>
        {reindexResult && (
          <p className="mt-2 text-sm text-green-700">{reindexResult}</p>
        )}
      </div>

      {/* File list */}
      {info?.local_files && info.local_files.length > 0 && (
        <div className="bg-white border rounded-lg p-5">
          <h3 className="font-semibold text-gray-700 mb-3">
            Documents ({info.local_files.length})
          </h3>
          <ul className="space-y-1 max-h-64 overflow-y-auto">
            {info.local_files.map((f) => (
              <li
                key={f}
                className="text-sm text-gray-600 py-1 border-b last:border-0"
              >
                📄 {f}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Glossary */}
      {glossary.length > 0 && (
        <div className="bg-white border rounded-lg p-5">
          <h3 className="font-semibold text-gray-700 mb-3">
            HR Vernacular Glossary ({glossary.length} terms)
          </h3>
          <p className="text-sm text-gray-500 mb-3">
            Maps informal terms to formal HR policy names for better search
            accuracy.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-72 overflow-y-auto">
            {glossary.map((g) => (
              <div
                key={g.vernacular}
                className="flex text-sm py-1 border-b"
              >
                <span className="font-mono text-azure-700 w-40 shrink-0">
                  {g.vernacular}
                </span>
                <span className="text-gray-600">→ {g.formal}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="bg-white border rounded-lg p-5 text-center">
      <p className="text-3xl font-bold text-azure-600">{value}</p>
      <p className="text-sm text-gray-500 mt-1">{label}</p>
    </div>
  );
}
