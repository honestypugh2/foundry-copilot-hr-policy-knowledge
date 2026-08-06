import { useEffect, useState } from "react";
import { Link, useLocation, useParams, useSearch } from "wouter";
import { AlertTriangle, ArrowRight, CheckCircle2, ChevronRight, ExternalLink, Gauge, ShieldCheck, Sparkles, Timer, Trophy } from "lucide-react";
import { benchmarkApi, type ComparisonResponse, type ExperimentSummary, type PatternSummaryResponse } from "../services/benchmarking";

const formatMs = (value: number | null) => value === null ? "Not measured" : `${Math.round(value)} ms`;
const formatRate = (value: number | null) => value === null ? "Not measured" : `${(value * 100).toFixed(1)}%`;

function useExperiments() {
  const [items, setItems] = useState<ExperimentSummary[]>([]);
  const [error, setError] = useState("");
  useEffect(() => void benchmarkApi.experiments().then((data) => setItems(data.items)).catch((reason: Error) => setError(reason.message)), []);
  return { items, error };
}

function State({ message }: { message: string }) { return <div className="state"><AlertTriangle size={18} />{message}</div>; }
function Metric({ label, value, detail }: { label: string; value: string; detail?: string }) { return <div className="metric"><span>{label}</span><strong>{value}</strong>{detail && <small>{detail}</small>}</div>; }

function ExperimentTable({ items }: { items: ExperimentSummary[] }) {
  if (!items.length) return <State message="No experiment artifacts are configured." />;
  return <div className="table-wrap"><table><thead><tr><th>Experiment</th><th>Pattern</th><th>p95 latency</th><th>Success</th><th>Quality</th><th>Evidence</th><th aria-label="Open" /></tr></thead><tbody>{items.map((item) => <tr key={item.experiment_id}><td><Link href={`/experiments/${item.experiment_id}`}>{item.experiment_id}</Link><small>{item.dataset_name} · v{item.dataset_version}</small></td><td><span className={`pattern pattern-${item.pattern.toLowerCase()}`}>{item.pattern}</span></td><td className="numeric">{formatMs(item.latency_p95_ms)}</td><td className="numeric">{formatRate(item.success_rate)}</td><td className="numeric">{formatRate(item.quality)}</td><td><span className={item.sample_warning ? "evidence-tag caution" : "evidence-tag"}>{item.sample_warning ? <AlertTriangle size={12} /> : <CheckCircle2 size={12} />}{item.count} samples</span>{item.provenance.synthetic === true && <small>Synthetic</small>}</td><td><Link className="row-action" aria-label={`Open ${item.experiment_id}`} href={`/experiments/${item.experiment_id}`}><ChevronRight size={17} /></Link></td></tr>)}</tbody></table></div>;
}

export function Overview() {
  const { items, error } = useExperiments();
  const [goal, setGoal] = useState<"quality" | "balanced" | "speed">("quality");
  if (error) return <State message={error} />;
  const ranked = items.filter((item) => item.quality !== null && item.latency_p95_ms !== null && !item.sample_warning);
  const recommended = [...ranked].sort((left, right) => {
    if (goal === "quality") return (right.quality ?? 0) - (left.quality ?? 0);
    if (goal === "speed") return (left.latency_p95_ms ?? Infinity) - (right.latency_p95_ms ?? Infinity);
    const leftScore = (left.quality ?? 0) * left.success_rate / Math.log10((left.latency_p95_ms ?? 0) + 10);
    const rightScore = (right.quality ?? 0) * right.success_rate / Math.log10((right.latency_p95_ms ?? 0) + 10);
    return rightScore - leftScore;
  })[0];
  const alternative = ranked.find((item) => item.experiment_id !== recommended?.experiment_id);
  const qualityDelta = recommended && alternative && recommended.quality !== null && alternative.quality !== null ? recommended.quality - alternative.quality : null;
  const speedRatio = recommended && alternative && recommended.latency_p95_ms && alternative.latency_p95_ms ? recommended.latency_p95_ms / alternative.latency_p95_ms : null;
  const synthetic = items.some((item) => item.provenance.synthetic === true || item.git_commit === "synthetic");
  const decisionText = goal === "quality" ? "Best answer quality" : goal === "speed" ? "Fastest trusted response" : "Best quality-to-latency balance";

  return <section className="page overview-page"><header className="page-head overview-head"><div><p className="eyebrow">Architecture decision intelligence</p><h1>Choose the right retrieval path.</h1><p className="lede">Turn controlled benchmark evidence into a clear architecture decision, with every tradeoff visible.</p></div><div className="evidence-summary"><span className="live-dot" /><div><strong>{items.length} runs analyzed</strong><small>{synthetic ? "Synthetic evidence · not production telemetry" : "Artifact-backed evidence"}</small></div></div></header>
    {recommended ? <><section className="decision-panel" aria-labelledby="recommendation-heading"><div className="decision-main"><div className="decision-kicker"><Sparkles size={16} /> Current recommendation</div><h2 id="recommendation-heading">Pattern {recommended.pattern}</h2><p>{decisionText} for the evidence currently available.</p><div className="decision-actions"><Link className="primary-action" href={`/experiments/${recommended.experiment_id}`}>Inspect evidence <ArrowRight size={16} /></Link><Link className="secondary-action" href={`/compare?baseline=${alternative?.experiment_id ?? recommended.experiment_id}&candidate=${recommended.experiment_id}`}>Compare paths</Link></div></div><div className="decision-controls"><span>Optimize recommendation for</span><div className="segment" role="group" aria-label="Recommendation goal">{(["quality", "balanced", "speed"] as const).map((option) => <button key={option} className={goal === option ? "active" : ""} aria-pressed={goal === option} onClick={() => setGoal(option)}>{option === "quality" ? <Trophy size={15} /> : option === "balanced" ? <Gauge size={15} /> : <Timer size={15} />}{option}</button>)}</div></div><div className="decision-metrics"><div><span>Quality</span><strong>{formatRate(recommended.quality)}</strong><div className="meter"><i style={{ width: `${(recommended.quality ?? 0) * 100}%` }} /></div>{qualityDelta !== null && <small>{qualityDelta >= 0 ? "+" : ""}{(qualityDelta * 100).toFixed(0)} pts vs alternative</small>}</div><div><span>p95 latency</span><strong>{formatMs(recommended.latency_p95_ms)}</strong><div className="meter latency"><i style={{ width: `${Math.min(100, ((recommended.latency_p95_ms ?? 0) / 750) * 100)}%` }} /></div>{speedRatio !== null && <small>{speedRatio > 1 ? `${speedRatio.toFixed(1)}× slower` : `${(1 / speedRatio).toFixed(1)}× faster`} than alternative</small>}</div><div><span>Successful answers</span><strong>{formatRate(recommended.success_rate)}</strong><small>{recommended.count} measured samples</small></div></div></section>
    <section className="insight-strip" aria-label="Decision notes"><div><strong>What this means</strong><p>{goal === "quality" ? `Pattern ${recommended.pattern} produces the strongest graded answers. Choose it when answer quality outweighs response time.` : goal === "speed" ? `Pattern ${recommended.pattern} returns trusted answers fastest. Choose it for latency-sensitive employee experiences.` : `Pattern ${recommended.pattern} currently offers the strongest combined quality, reliability, and latency score.`}</p></div><div><strong>Evidence boundary</strong><p>{synthetic ? "Results are synthetic and suitable for architecture comparison, not production claims." : "Results come from normalized controlled-run artifacts."}</p></div><div><strong>Next decision</strong><p>{alternative ? `Validate Pattern ${recommended.pattern} and Pattern ${alternative.pattern} with the same production-like question set.` : "Run another architecture pattern against this same dataset."}</p></div></section></> : <section className="empty-decision"><div><Sparkles size={22} /><h2>No decision evidence yet</h2><p>Run at least one benchmark with quality and latency measurements to generate a recommendation.</p><Link className="primary-action" href="/patterns">Review benchmark paths <ArrowRight size={16} /></Link></div></section>}
    <div className="section-title"><div><p className="eyebrow">Evidence ledger</p><h3>Every run, side by side</h3></div><Link href="/experiments">Explore all experiments <ArrowRight size={15} /></Link></div><ExperimentTable items={items.slice(0, 6)} /></section>;
}

export function Experiments() { const { items, error } = useExperiments(); return <section className="page"><header className="page-head"><div><p className="eyebrow">Controlled runs</p><h2>Experiments</h2></div></header>{error ? <State message={error} /> : <ExperimentTable items={items} />}</section>; }

export function ExperimentDetail() {
  const { id = "" } = useParams(); const { items, error } = useExperiments(); const item = items.find((candidate) => candidate.experiment_id === id);
  if (error) return <State message={error} />; if (!item) return <State message="Experiment not found or still loading." />;
  return <section className="page"><header className="page-head"><div><p className="eyebrow">Experiment detail</p><h2>{item.experiment_id}</h2></div><span className="pattern">Pattern {item.pattern}</span></header><div className="metrics"><Metric label="p50" value={formatMs(item.latency_p50_ms)} /><Metric label="p95" value={formatMs(item.latency_p95_ms)} /><Metric label="p99" value={formatMs(item.latency_p99_ms)} /><Metric label="Success" value={formatRate(item.success_rate)} /></div><div className="detail-grid"><article><h3>Reproducibility</h3><dl><dt>Git commit</dt><dd>{item.git_commit}</dd><dt>Corpus</dt><dd>{item.corpus_fingerprint ?? "Not recorded"}</dd><dt>Index</dt><dd>{item.index_fingerprint ?? "Not recorded"}</dd><dt>Model</dt><dd>{item.model_deployment ?? "Not applicable"}</dd></dl></article><article><h3>Evidence boundary</h3><p>Values shown here come from the normalized experiment artifact. Production telemetry is intentionally separate.</p>{item.sample_warning && <State message={item.sample_warning} />}</article></div></section>;
}

export function Compare() {
  const { items, error } = useExperiments(); const [, navigate] = useLocation(); const search = useSearch(); const params = new URLSearchParams(search); const baseline = params.get("baseline") ?? items[0]?.experiment_id ?? ""; const candidate = params.get("candidate") ?? items[1]?.experiment_id ?? ""; const [comparison, setComparison] = useState<ComparisonResponse | null>(null);
  const setParams = (nextBaseline: string, nextCandidate: string) => navigate(`/compare?${new URLSearchParams({ baseline: nextBaseline, candidate: nextCandidate })}`);
  useEffect(() => { if (baseline && candidate) void benchmarkApi.compare(baseline, candidate).then(setComparison); }, [baseline, candidate]);
  if (error) return <State message={error} />;
  return <section className="page"><header className="page-head"><div><p className="eyebrow">Controlled comparison</p><h2>Compare runs</h2></div></header><div className="selectors"><label>Baseline<select value={baseline} onChange={(event) => setParams(event.target.value, candidate)}>{items.map((item) => <option key={item.experiment_id}>{item.experiment_id}</option>)}</select></label><label>Candidate<select value={candidate} onChange={(event) => setParams(baseline, event.target.value)}>{items.map((item) => <option key={item.experiment_id}>{item.experiment_id}</option>)}</select></label></div>{comparison && <><div className={comparison.compatible_scope ? "scope good" : "scope bad"}>{comparison.compatible_scope ? <ShieldCheck size={18} /> : <AlertTriangle size={18} />}{comparison.compatible_scope ? "Comparable dataset and configuration scope" : comparison.incompatibility_reasons.join("; ")}</div><div className="metrics">{Object.entries(comparison.deltas).map(([name, delta]) => <Metric key={name} label={name.replace(/_/g, " ")} value={delta.absolute === null ? "Not comparable" : `${delta.absolute > 0 ? "+" : ""}${delta.absolute.toFixed(3)}`} detail={delta.relative === null ? undefined : `${(delta.relative * 100).toFixed(1)}%`} />)}</div></>}</section>;
}

export function Patterns() {
  const patterns = ["A", "A2", "B", "C", "Hosted"]; const [items, setItems] = useState<PatternSummaryResponse["item"][]>([]);
  useEffect(() => void Promise.all(patterns.map((pattern) => benchmarkApi.pattern(pattern))).then((values) => setItems(values.map((value) => value.item))), []);
  return <section className="page"><header className="page-head"><div><p className="eyebrow">Execution paths</p><h2>Pattern evidence</h2></div></header><div className="pattern-grid">{items.map((item) => <article key={item.pattern}><div className="pattern-label">{item.pattern}</div><h3>{item.experiment_count} experiments</h3><p>{item.automation_boundary}</p><small>{item.telemetry_boundary}</small></article>)}</div></section>;
}

export function Pareto() { const { items, error } = useExperiments(); if (error) return <State message={error} />; const points = items.filter((item) => item.latency_p95_ms !== null && item.quality !== null); return <section className="page"><header className="page-head"><div><p className="eyebrow">Quality versus latency</p><h2>Pareto and SLO</h2></div></header><div className="plot" aria-label="Quality and latency plot">{points.map((item) => <Link title={`${item.experiment_id}: ${formatMs(item.latency_p95_ms)}, ${formatRate(item.quality)}`} href={`/experiments/${item.experiment_id}`} className="plot-point" key={item.experiment_id} style={{ left: `${Math.min(90, 8 + (item.latency_p95_ms ?? 0) / 3)}%`, bottom: `${Math.min(90, 8 + (item.quality ?? 0) * 80)}%` }}><span>{item.pattern}</span></Link>)}<span className="x-label">p95 latency →</span><span className="y-label">quality →</span></div></section>; }

export function Operations() {
  const resources = [
    ["Application Insights", "application_insights"],
    ["Azure AI Search", "search"],
    ["Foundry", "foundry"],
    ["Load Testing", "load_testing"],
  ] as const;
  const [links, setLinks] = useState<Record<string, { status: string; url?: string }>>({});
  useEffect(() => {
    void Promise.all(resources.map(async ([, type]) => {
      const result = await benchmarkApi.nativeLink(type, "current");
      return [type, { status: result.status, url: result.authoritative_url ?? undefined }] as const;
    })).then((items) => setLinks(Object.fromEntries(items)));
  }, []);
  return <section className="page"><header className="page-head"><div><p className="eyebrow">Authoritative systems</p><h2>Operations</h2></div></header><div className="ops-grid">{resources.map(([label, type]) => <article key={type}><ExternalLink size={19} /><h3>{label}</h3><p>Server-managed deep link to the authoritative investigation surface.</p>{links[type]?.url ? <a href={links[type].url} target="_blank" rel="noreferrer">Open {label}</a> : <span className="status muted">{links[type]?.status?.replace(/_/g, " ") ?? "Loading"}</span>}</article>)}</div></section>;
}

export function Provenance() { const { items, error } = useExperiments(); if (error) return <State message={error} />; return <section className="page"><header className="page-head"><div><p className="eyebrow">Audit trail</p><h2>Provenance</h2></div></header><div className="table-wrap"><table><thead><tr><th>Experiment</th><th>Commit</th><th>Corpus fingerprint</th><th>Index fingerprint</th></tr></thead><tbody>{items.map((item) => <tr key={item.experiment_id}><td>{item.experiment_id}</td><td><code>{item.git_commit}</code></td><td><code>{item.corpus_fingerprint ?? "not recorded"}</code></td><td><code>{item.index_fingerprint ?? "not recorded"}</code></td></tr>)}</tbody></table></div></section>; }