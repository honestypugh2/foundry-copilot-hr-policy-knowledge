// Original schematic of the agentic-retrieval phases (query planning -> fan-out -> merge).
export default function AgenticFlow() {
  return (
    <svg className="agentic-flow" viewBox="0 0 760 214" role="img" aria-label="Agentic retrieval phases: query planning fans out sub-queries that are searched in parallel and merged.">
      <defs>
        <marker id="af-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" className="af-arrowhead" />
        </marker>
      </defs>

      {/* edges */}
      <path className="af-edge" d="M150,107 H186" markerEnd="url(#af-arrow)" />
      <path className="af-edge" d="M330,107 C352,107 352,44 374,44" markerEnd="url(#af-arrow)" />
      <path className="af-edge" d="M330,107 H374" markerEnd="url(#af-arrow)" />
      <path className="af-edge" d="M330,107 C352,107 352,170 374,170" markerEnd="url(#af-arrow)" />
      <path className="af-edge" d="M536,44 C560,44 560,107 582,107" markerEnd="url(#af-arrow)" />
      <path className="af-edge" d="M536,107 H582" markerEnd="url(#af-arrow)" />
      <path className="af-edge" d="M536,170 C560,170 560,107 582,107" markerEnd="url(#af-arrow)" />

      {/* user query */}
      <g>
        <rect className="af-box af-box-input" x="8" y="83" width="142" height="48" rx="9" />
        <text className="af-box-title" x="79" y="103">User query</text>
        <text className="af-box-sub" x="79" y="119">+ conversation history</text>
      </g>

      {/* query planning */}
      <g>
        <rect className="af-box af-box-plan" x="186" y="79" width="144" height="56" rx="9" />
        <text className="af-box-title" x="258" y="101">Query planning</text>
        <text className="af-box-sub" x="258" y="117">1 LLM call → sub-queries</text>
        <text className="af-phase af-phase-plan" x="258" y="150">modelQueryPlanning</text>
      </g>

      {/* fan-out searches */}
      <g>
        <rect className="af-box af-box-search" x="374" y="24" width="162" height="40" rx="9" />
        <text className="af-box-title sm" x="455" y="48">Search sub-query 1</text>
        <rect className="af-box af-box-search" x="374" y="87" width="162" height="40" rx="9" />
        <text className="af-box-title sm" x="455" y="111">Search sub-query 2</text>
        <rect className="af-box af-box-search" x="374" y="150" width="162" height="40" rx="9" />
        <text className="af-box-title sm" x="455" y="174">Search sub-query n</text>
        <text className="af-phase af-phase-search" x="455" y="206">searchIndex (parallel)</text>
      </g>

      {/* merge + reason */}
      <g>
        <rect className="af-box af-box-merge" x="582" y="79" width="170" height="56" rx="9" />
        <text className="af-box-title" x="667" y="101">Merge + rank</text>
        <text className="af-box-sub" x="667" y="117">unified answer + citations</text>
        <text className="af-phase af-phase-merge" x="667" y="150">agenticReasoning</text>
      </g>
    </svg>
  );
}
