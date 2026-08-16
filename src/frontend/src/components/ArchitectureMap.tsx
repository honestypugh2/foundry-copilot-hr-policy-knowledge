import { useState } from "react";
import { Link } from "wouter";
import { ArrowRight, Sparkles } from "lucide-react";

type PatternNode = {
  id: string;
  color: string;
  title: string;
  backend: string;
  lane: string;
  modes: string[];
  blurb: string;
};

const PATTERNS: PatternNode[] = [
  { id: "A", color: "#2563eb", title: "Azure AI Search knowledge", backend: "Classic hybrid + semantic ranking", lane: "front door", modes: ["hybrid-semantic"], blurb: "Copilot Studio queries an Azure AI Search index directly — keyword + vector hybrid with semantic reranking." },
  { id: "A2", color: "#7c3aed", title: "Foundry IQ agentic KB", backend: "Agentic Knowledge Base retrieval", lane: "front door", modes: ["agentic-retrieval"], blurb: "Foundry IQ plans sub-queries against a Knowledge Base, then synthesizes a grounded answer." },
  { id: "B", color: "#0ea5e9", title: "Foundry Agent Service", backend: "Prompt agent + MCP tool", lane: "deployed", modes: ["tool"], blurb: "Copilot Studio hands off to a deployed Foundry prompt agent that retrieves through an MCP tool." },
  { id: "C", color: "#0d9488", title: "Deterministic locator", backend: "Dual-tool routing", lane: "front door", modes: ["hybrid-semantic-with-deterministic-locator"], blurb: "A deterministic document locator resolves exact policy IDs, with hybrid semantic search as the fallback tool." },
  { id: "Hosted", color: "#e0562f", title: "Self-hosted Agent Framework", backend: "Container runtime", lane: "local · deployed", modes: ["tool", "context-semantic", "context-agentic"], blurb: "Copilot Studio calls a self-hosted Agent Framework container — measured both locally (in-process SDK) and deployed." },
];

const HUB = { x: 216, y: 196, w: 194, h: 128 };
const nodeTop = (index: number) => 18 + index * 100;
const nodeCenterY = (index: number) => nodeTop(index) + 40;

/** Interactive, animated map of the Copilot Studio front door routing into every pattern and its retrieval options. */
export default function ArchitectureMap({ runByPattern }: { runByPattern?: Record<string, string> }) {
  const [active, setActive] = useState<string>("A2");
  const activePattern = PATTERNS.find((pattern) => pattern.id === active) ?? PATTERNS[0];

  return (
    <section className="arch-map" aria-label="Architecture map">
      <div className="section-title">
        <div>
          <p className="eyebrow">Architecture map</p>
          <h2>One front door, five grounded-agent patterns</h2>
          <p>Employees always enter through Copilot Studio. From there each pattern routes retrieval a different way — hover or tap a pattern to trace its path and see its options.</p>
        </div>
      </div>

      <div className="arch-canvas">
        <svg viewBox="0 0 1000 520" role="img" aria-label="Copilot Studio front door routing to five patterns" className="arch-svg">
          <defs>
            <linearGradient id="hubGrad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stopColor="#3b82f6" />
              <stop offset="1" stopColor="#6366f1" />
            </linearGradient>
          </defs>

          {/* Employee -> hub */}
          <path className="arch-link base" d="M154 260 H212" />
          {PATTERNS.map((pattern, index) => {
            const cY = nodeCenterY(index);
            const isActive = pattern.id === active;
            return (
              <path
                key={`link-${pattern.id}`}
                className={isActive ? "arch-link flow" : "arch-link base"}
                style={isActive ? { stroke: pattern.color } : undefined}
                d={`M410 260 C 492 260 484 ${cY} 560 ${cY}`}
                fill="none"
              />
            );
          })}

          {/* Employee node */}
          <g className="arch-node-static">
            <rect x="24" y="228" width="130" height="64" rx="12" />
            <text x="89" y="255" textAnchor="middle" className="arch-node-title">Employee</text>
            <text x="89" y="274" textAnchor="middle" className="arch-node-sub">Teams · M365</text>
          </g>

          {/* Copilot Studio front door hub */}
          <g className="arch-hub">
            <circle className="arch-pulse" cx={HUB.x + HUB.w / 2} cy={HUB.y + HUB.h / 2} r="82" />
            <circle className="arch-pulse delay" cx={HUB.x + HUB.w / 2} cy={HUB.y + HUB.h / 2} r="82" />
            <rect x={HUB.x} y={HUB.y} width={HUB.w} height={HUB.h} rx="18" fill="url(#hubGrad)" />
            <text x={HUB.x + HUB.w / 2} y={HUB.y + 52} textAnchor="middle" className="arch-hub-title">Copilot Studio</text>
            <text x={HUB.x + HUB.w / 2} y={HUB.y + 78} textAnchor="middle" className="arch-hub-sub">front door</text>
            <text x={HUB.x + HUB.w / 2} y={HUB.y + 102} textAnchor="middle" className="arch-hub-note">orchestration · channels</text>
          </g>

          {/* Pattern nodes */}
          {PATTERNS.map((pattern, index) => {
            const top = nodeTop(index);
            const isActive = pattern.id === active;
            const shortId = pattern.id === "Hosted" ? "H" : pattern.id;
            return (
              <g
                key={pattern.id}
                className={isActive ? "arch-node active" : "arch-node"}
                transform={`translate(560 ${top})`}
                role="button"
                tabIndex={0}
                aria-pressed={isActive}
                onMouseEnter={() => setActive(pattern.id)}
                onFocus={() => setActive(pattern.id)}
                onClick={() => setActive(pattern.id)}
                onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") setActive(pattern.id); }}
              >
                <rect x="0" y="0" width="416" height="80" rx="14" className="arch-node-box" style={isActive ? { stroke: pattern.color } : undefined} />
                <rect x="0" y="0" width="6" height="80" rx="3" fill={pattern.color} />
                <circle cx="40" cy="40" r="18" fill={pattern.color} />
                <text x="40" y="45" textAnchor="middle" className="arch-node-badge">{shortId}</text>
                <text x="72" y="34" className="arch-node-title">{pattern.title}</text>
                <text x="72" y="58" className="arch-node-sub">{pattern.backend}</text>
                <text x="404" y="58" textAnchor="end" className="arch-node-lane" style={{ fill: pattern.color }}>{pattern.lane} · {pattern.modes.length} opt{pattern.modes.length === 1 ? "" : "s"}</text>
              </g>
            );
          })}
        </svg>
      </div>

      <div className="arch-detail" style={{ borderColor: activePattern.color }}>
        <div className="arch-detail-head">
          <span className="arch-detail-badge" style={{ background: activePattern.color }}>{activePattern.id}</span>
          <div>
            <h3>{activePattern.title}</h3>
            <p>{activePattern.blurb}</p>
          </div>
        </div>
        <div className="arch-detail-meta">
          <div><span className="arch-meta-label">Retrieval backend</span><strong>{activePattern.backend}</strong></div>
          <div><span className="arch-meta-label">Measurement lane</span><strong>{activePattern.lane}</strong></div>
          <div>
            <span className="arch-meta-label">Retrieval options</span>
            <span className="arch-mode-chips">{activePattern.modes.map((mode) => <code key={mode}>{mode}</code>)}</span>
          </div>
        </div>
        {runByPattern?.[activePattern.id] && (
          <Link className="arch-detail-link" href={`/experiments/${runByPattern[activePattern.id]}`}>
            <Sparkles size={14} /> Inspect the latest {activePattern.id} run <ArrowRight size={14} />
          </Link>
        )}
      </div>
    </section>
  );
}
