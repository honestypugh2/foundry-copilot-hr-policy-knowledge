import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  Legend,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import type { ExperimentSummary } from "../services/benchmarking";

// SLO gate thresholds shared with the Pareto/SLO view.
const SLO_P95_MS = 30000;
const SLO_QUALITY_PCT = 85;

const PATTERN_ORDER = ["A", "A2", "B", "C", "Hosted"] as const;
const PATTERN_COLOR: Record<string, string> = {
  A: "#2563eb",
  A2: "#7c3aed",
  B: "#0ea5e9",
  C: "#0d9488",
  Hosted: "#e0562f",
};
const colorFor = (pattern: string) => PATTERN_COLOR[pattern] ?? "#64748b";

export interface PatternRow {
  pattern: string;
  p50s: number | null;
  p95s: number | null;
  quality: number | null;
  security: number | null;
  cost: number | null;
  count: number;
  experimentId: string;
}

const pct = (value: number | null | undefined) =>
  value === null || value === undefined ? null : Number((value * 100).toFixed(1));
const secs = (ms: number | null | undefined) =>
  ms === null || ms === undefined ? null : Number((ms / 1000).toFixed(1));
const creditsPerInteraction = (item: ExperimentSummary): number | null => {
  const credits = (item.provenance as Record<string, unknown> | undefined)?.copilot_credits as
    | Record<string, unknown>
    | undefined;
  return typeof credits?.credits_per_interaction === "number"
    ? credits.credits_per_interaction
    : null;
};

/** Pick the most-evidenced graded run per pattern for the at-a-glance charts. */
export function summarizeByPattern(items: ExperimentSummary[]): PatternRow[] {
  return PATTERN_ORDER.map((pattern) => {
    const graded = items
      .filter((item) => item.pattern === pattern && item.quality !== null)
      .sort((a, b) => b.count - a.count || b.created_at.localeCompare(a.created_at));
    const anyRun = items
      .filter((item) => item.pattern === pattern)
      .sort((a, b) => b.count - a.count)[0];
    const best = graded[0] ?? anyRun;
    return {
      pattern,
      p50s: secs(best?.latency_p50_ms),
      p95s: secs(best?.latency_p95_ms),
      quality: pct(best?.quality),
      security: pct(best?.security_pass_rate),
      cost: best?.estimated_variable_cost ?? null,
      count: best?.count ?? 0,
      experimentId: best?.experiment_id ?? "",
    };
  }).filter((row) => row.count > 0 || row.p95s !== null || row.quality !== null);
}

const AXIS = { fontSize: 13, fill: "var(--ink-soft)", fontWeight: 600 } as const;
const tooltipStyle = {
  borderRadius: 12,
  border: "1px solid var(--line)",
  boxShadow: "0 12px 30px rgba(15,23,42,.14)",
  fontSize: 13,
  padding: "10px 12px",
} as const;

function ChartCard({
  eyebrow,
  title,
  hint,
  children,
}: {
  eyebrow: string;
  title: string;
  hint: string;
  children: React.ReactNode;
}) {
  return (
    <article className="chart-card">
      <header className="chart-card-head">
        <p className="eyebrow">{eyebrow}</p>
        <h3>{title}</h3>
        <p className="chart-hint">{hint}</p>
      </header>
      <div className="chart-body">{children}</div>
    </article>
  );
}

export default function BenchmarkCharts({ items }: { items: ExperimentSummary[] }) {
  const rows = summarizeByPattern(items);
  if (!rows.length) return null;
  const latencyRows = rows.filter((row) => row.p95s !== null);
  const qualityRows = rows.filter((row) => row.quality !== null);
  const scatterRows = rows.filter((row) => row.p95s !== null && row.quality !== null);
  const creditRows = PATTERN_ORDER.map((pattern) => {
    const run = items
      .filter((item) => item.pattern === pattern && creditsPerInteraction(item) !== null)
      .sort((a, b) => b.count - a.count || b.created_at.localeCompare(a.created_at))[0];
    return run
      ? { pattern: String(pattern), credits: creditsPerInteraction(run) as number }
      : null;
  }).filter((row): row is { pattern: string; credits: number } => row !== null);
  const costRows = PATTERN_ORDER.map((pattern) => {
    const run = items
      .filter(
        (item) =>
          item.pattern === pattern &&
          item.estimated_variable_cost !== null &&
          (item.provenance as Record<string, unknown> | undefined)?.synthetic !== true,
      )
      .sort((a, b) => b.count - a.count || b.created_at.localeCompare(a.created_at))[0];
    return run ? { pattern: String(pattern), cost: run.estimated_variable_cost as number } : null;
  }).filter((row): row is { pattern: string; cost: number } => row !== null);

  return (
    <section className="charts-panel" aria-label="Benchmark at a glance">
      <div className="section-title charts-title">
        <div>
          <p className="eyebrow">Benchmark at a glance</p>
          <h2>Five architectures, one workload — measured</h2>
          <p>
            Latency, answer quality, security, the quality-vs-speed trade-off, and
            cost across Patterns A, A2, B, C, and Hosted. Cost has two lanes that
            cannot be combined: Copilot Studio bills Copilot Credits per agent
            activity; Foundry
            prices tokens per answer. Lower latency, higher quality, lower cost are better.
          </p>
        </div>
      </div>

      <div className="charts-grid">
        <ChartCard
          eyebrow="Latency"
          title="Response time by architecture"
          hint="Client wall-time p50 (typical) and p95 (slow tail), in seconds."
        >
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={latencyRows} margin={{ top: 8, right: 8, left: -8, bottom: 0 }} barGap={6}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" vertical={false} />
              <XAxis dataKey="pattern" tick={AXIS} axisLine={false} tickLine={false} />
              <YAxis tick={AXIS} axisLine={false} tickLine={false} unit="s" width={44} />
              <Tooltip
                contentStyle={tooltipStyle}
                cursor={{ fill: "rgba(37,99,235,.06)" }}
                formatter={(value, name) => [`${value}s`, name === "p50s" ? "p50 typical" : "p95 tail"]}
              />
              <Legend
                iconType="circle"
                formatter={(value) => (value === "p50s" ? "p50 · typical" : "p95 · slow tail")}
                wrapperStyle={{ fontSize: 12.5, fontWeight: 600 }}
              />
              <Bar dataKey="p50s" fill="#93c5fd" radius={[6, 6, 0, 0]} maxBarSize={34} />
              <Bar dataKey="p95s" fill="#2563eb" radius={[6, 6, 0, 0]} maxBarSize={34} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard
          eyebrow="Quality vs speed"
          title="Pareto trade-off with SLO gate"
          hint="Top-left is best. Shaded zone passes the release gate (quality ≥ 85%, p95 ≤ 30s)."
        >
          <ResponsiveContainer width="100%" height={260}>
            <ScatterChart margin={{ top: 12, right: 16, left: -8, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
              <XAxis
                type="number"
                dataKey="p95s"
                name="p95 latency"
                unit="s"
                tick={AXIS}
                axisLine={false}
                tickLine={false}
                domain={[0, "dataMax + 10"]}
              />
              <YAxis
                type="number"
                dataKey="quality"
                name="quality"
                unit="%"
                tick={AXIS}
                axisLine={false}
                tickLine={false}
                domain={[0, 100]}
                width={52}
              />
              <ZAxis type="number" dataKey="count" range={[120, 460]} name="samples" />
              <ReferenceArea
                x1={0}
                x2={SLO_P95_MS / 1000}
                y1={SLO_QUALITY_PCT}
                y2={100}
                fill="#16a34a"
                fillOpacity={0.08}
                stroke="#16a34a"
                strokeOpacity={0.25}
              />
              <ReferenceLine x={SLO_P95_MS / 1000} stroke="#94a3b8" strokeDasharray="4 4" />
              <ReferenceLine y={SLO_QUALITY_PCT} stroke="#94a3b8" strokeDasharray="4 4" />
              <Tooltip
                contentStyle={tooltipStyle}
                cursor={{ strokeDasharray: "3 3" }}
                formatter={(value, name) =>
                  name === "quality" ? [`${value}%`, "Quality"] : name === "p95 latency" ? [`${value}s`, "p95"] : [value, name]
                }
              />
              <Scatter data={scatterRows} fill="#2563eb">
                {scatterRows.map((row) => (
                  <Cell key={row.pattern} fill={colorFor(row.pattern)} />
                ))}
                <LabelList dataKey="pattern" position="top" style={{ fontSize: 12.5, fontWeight: 700, fill: "var(--ink)" }} />
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard
          eyebrow="Quality & security"
          title="Deterministic gates by architecture"
          hint="Deterministic quality and security pass rates; judges are supplemental."
        >
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={qualityRows} margin={{ top: 8, right: 8, left: -8, bottom: 0 }} barGap={6}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" vertical={false} />
              <XAxis dataKey="pattern" tick={AXIS} axisLine={false} tickLine={false} />
              <YAxis tick={AXIS} axisLine={false} tickLine={false} unit="%" domain={[0, 100]} width={52} />
              <Tooltip
                contentStyle={tooltipStyle}
                cursor={{ fill: "rgba(37,99,235,.06)" }}
                formatter={(value, name) => [`${value}%`, name === "quality" ? "Quality" : "Security"]}
              />
              <Legend iconType="circle" formatter={(v) => (v === "quality" ? "Quality" : "Security")} wrapperStyle={{ fontSize: 12.5, fontWeight: 600 }} />
              <ReferenceLine y={SLO_QUALITY_PCT} stroke="#16a34a" strokeDasharray="4 4" />
              <Bar dataKey="quality" fill="#2563eb" radius={[6, 6, 0, 0]} maxBarSize={30}>
                <LabelList dataKey="quality" position="top" formatter={(v) => `${v}%`} style={{ fontSize: 11.5, fontWeight: 700, fill: "var(--ink-soft)" }} />
              </Bar>
              <Bar dataKey="security" fill="#14b8a6" radius={[6, 6, 0, 0]} maxBarSize={30} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        {creditRows.length > 0 && (
          <ChartCard
            eyebrow="Cost · Copilot Studio lane"
            title="Credits per interaction"
            hint="Patterns A, A2, C bill in Copilot Credits, rated per agent activity — Microsoft-managed, not convertible to USD."
          >
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={creditRows} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" vertical={false} />
                <XAxis dataKey="pattern" tick={AXIS} axisLine={false} tickLine={false} />
                <YAxis tick={AXIS} axisLine={false} tickLine={false} width={44} />
                <Tooltip
                  contentStyle={tooltipStyle}
                  cursor={{ fill: "rgba(37,99,235,.06)" }}
                  formatter={(value) => [`${value} credits/interaction`, "Credits"]}
                />
                <Bar dataKey="credits" radius={[6, 6, 0, 0]} maxBarSize={44}>
                  {creditRows.map((row) => (
                    <Cell key={row.pattern} fill={colorFor(row.pattern)} />
                  ))}
                  <LabelList dataKey="credits" position="top" style={{ fontSize: 11.5, fontWeight: 700, fill: "var(--ink-soft)" }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        )}

        {costRows.length > 0 && (
          <ChartCard
            eyebrow="Cost · Foundry token lane"
            title="Model cost per answer"
            hint="Patterns B, Hosted priced from token usage × pricing profile (USD/answer). Excludes Search, hosting, evaluators."
          >
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={costRows} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" vertical={false} />
                <XAxis dataKey="pattern" tick={AXIS} axisLine={false} tickLine={false} />
                <YAxis tick={AXIS} axisLine={false} tickLine={false} width={70} tickFormatter={(value) => `$${Number(value).toFixed(4)}`} />
                <Tooltip
                  contentStyle={tooltipStyle}
                  cursor={{ fill: "rgba(37,99,235,.06)" }}
                  formatter={(value) => [`$${Number(value).toFixed(4)}/answer`, "Est. cost"]}
                />
                <Bar dataKey="cost" radius={[6, 6, 0, 0]} maxBarSize={44}>
                  {costRows.map((row) => (
                    <Cell key={row.pattern} fill={colorFor(row.pattern)} />
                  ))}
                  <LabelList dataKey="cost" position="top" formatter={(value) => `$${Number(value).toFixed(4)}`} style={{ fontSize: 11, fontWeight: 700, fill: "var(--ink-soft)" }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        )}
      </div>
    </section>
  );
}

/** Horizontal p95 latency bar per run — the Experiments ledger visual (distinct from the pattern-summary charts). */
export function RunLatencyChart({ items }: { items: ExperimentSummary[] }) {
  const data = items
    .filter((item) => item.latency_p95_ms !== null)
    .map((item) => ({ id: item.experiment_id, s: secs(item.latency_p95_ms), fill: colorFor(item.pattern) }))
    .sort((a, b) => (b.s ?? 0) - (a.s ?? 0));
  if (!data.length) return null;
  const height = Math.max(160, data.length * 26 + 44);
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 52, left: 8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" horizontal={false} />
        <XAxis type="number" tick={AXIS} axisLine={false} tickLine={false} unit="s" />
        <YAxis type="category" dataKey="id" tick={{ ...AXIS, fontSize: 11 }} axisLine={false} tickLine={false} width={300} interval={0} tickFormatter={(value) => String(value).replace(/-\d+-\d+$/, "").replace(/-[0-9a-f]{6,}$/, "")} />
        <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "rgba(37,99,235,.06)" }} formatter={(v) => [`${v}s`, "p95"]} />
        <ReferenceLine x={SLO_P95_MS / 1000} stroke="#94a3b8" strokeDasharray="4 4" />
        <Bar dataKey="s" radius={[0, 6, 6, 0]} maxBarSize={18}>
          {data.map((row) => <Cell key={row.id} fill={row.fill} />)}
          <LabelList dataKey="s" position="right" formatter={(v) => `${v}s`} style={{ fontSize: 11, fontWeight: 700, fill: "var(--ink-soft)" }} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Horizontal p50/p95/p99 latency bars for a single run's detail page. */
export function SingleRunLatencyChart({ p50, p95, p99 }: { p50: number | null; p95: number | null; p99: number | null }) {
  const data = [
    { label: "p50 · typical", s: secs(p50), fill: "#93c5fd" },
    { label: "p95 · slow tail", s: secs(p95), fill: "#2563eb" },
    { label: "p99 · extreme", s: secs(p99), fill: "#1d4ed8" },
  ].filter((row) => row.s !== null);
  if (!data.length) return null;
  return (
    <ResponsiveContainer width="100%" height={190}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 44, left: 8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" horizontal={false} />
        <XAxis type="number" tick={AXIS} axisLine={false} tickLine={false} unit="s" />
        <YAxis type="category" dataKey="label" tick={AXIS} axisLine={false} tickLine={false} width={110} />
        <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "rgba(37,99,235,.06)" }} formatter={(v) => [`${v}s`, "latency"]} />
        <Bar dataKey="s" radius={[0, 6, 6, 0]} maxBarSize={26}>
          {data.map((row) => <Cell key={row.label} fill={row.fill} />)}
          <LabelList dataKey="s" position="right" formatter={(v) => `${v}s`} style={{ fontSize: 12, fontWeight: 700, fill: "var(--ink-soft)" }} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export interface ParetoPoint {
  experimentId: string;
  pattern: string;
  p95s: number;
  quality: number;
  count: number;
  onFrontier: boolean;
}

/** Recharts Pareto scatter (quality vs p95) with the SLO pass-zone. */
export function ParetoScatter({ points }: { points: ParetoPoint[] }) {
  if (!points.length) return null;
  return (
    <ResponsiveContainer width="100%" height={360}>
      <ScatterChart margin={{ top: 16, right: 24, left: 4, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
        <XAxis type="number" dataKey="p95s" name="p95 latency" unit="s" tick={AXIS} axisLine={false} tickLine={false} domain={[0, "dataMax + 6"]} />
        <YAxis type="number" dataKey="quality" name="quality" unit="%" tick={AXIS} axisLine={false} tickLine={false} domain={[0, 100]} width={52} />
        <ZAxis type="number" dataKey="count" range={[150, 540]} name="samples" />
        <ReferenceArea x1={0} x2={SLO_P95_MS / 1000} y1={SLO_QUALITY_PCT} y2={100} fill="#16a34a" fillOpacity={0.08} stroke="#16a34a" strokeOpacity={0.25} />
        <ReferenceLine x={SLO_P95_MS / 1000} stroke="#94a3b8" strokeDasharray="4 4" />
        <ReferenceLine y={SLO_QUALITY_PCT} stroke="#94a3b8" strokeDasharray="4 4" />
        <Tooltip
          contentStyle={tooltipStyle}
          cursor={{ strokeDasharray: "3 3" }}
          formatter={(value, name) => (name === "quality" ? [`${value}%`, "Quality"] : name === "p95 latency" ? [`${value}s`, "p95"] : [value, name])}
        />
        <Scatter data={points}>
          {points.map((p) => (
            <Cell key={p.experimentId} fill={colorFor(p.pattern)} stroke={p.onFrontier ? "#0f172a" : "#ffffff"} strokeWidth={p.onFrontier ? 2.5 : 1} />
          ))}
          <LabelList dataKey="pattern" position="top" style={{ fontSize: 12.5, fontWeight: 700, fill: "var(--ink)" }} />
        </Scatter>
      </ScatterChart>
    </ResponsiveContainer>
  );
}

interface CompareSide {
  id: string;
  p95s: number | null;
  quality: number | null;
}

/** Grouped bars comparing baseline vs candidate p95 (s) and quality (%). */
export function CompareChart({ baseline, candidate }: { baseline: CompareSide; candidate: CompareSide }) {
  const data = [
    { metric: "p95 latency (s)", baseline: baseline.p95s, candidate: candidate.p95s },
    { metric: "Quality (%)", baseline: baseline.quality, candidate: candidate.quality },
  ];
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -8, bottom: 0 }} barGap={8}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" vertical={false} />
        <XAxis dataKey="metric" tick={AXIS} axisLine={false} tickLine={false} />
        <YAxis tick={AXIS} axisLine={false} tickLine={false} width={44} />
        <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "rgba(37,99,235,.06)" }} />
        <Legend iconType="circle" wrapperStyle={{ fontSize: 12, fontWeight: 600 }} />
        <Bar dataKey="baseline" name={baseline.id.slice(0, 26)} fill="#93c5fd" radius={[6, 6, 0, 0]} maxBarSize={44} />
        <Bar dataKey="candidate" name={candidate.id.slice(0, 26)} fill="#2563eb" radius={[6, 6, 0, 0]} maxBarSize={44} />
      </BarChart>
    </ResponsiveContainer>
  );
}
