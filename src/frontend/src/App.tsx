import { Link, Route, Switch, useLocation } from "wouter";
import { Activity, Bot, Database, Gauge, GitCompareArrows, Library, Network, ScrollText } from "lucide-react";
import AboutPage from "./pages/AboutPage";
import { Compare, ExperimentDetail, Experiments, Operations, Overview, Pareto, Patterns, Provenance } from "./pages/BenchmarkWorkbench";
import ChatPage from "./pages/ChatPage";
import KnowledgeBasePage from "./pages/KnowledgeBasePage";

export default function App() {
  const [location] = useLocation();
  const links = [
    ["/", "Overview", Gauge], ["/experiments", "Experiments", Activity],
    ["/compare", "Compare", GitCompareArrows], ["/patterns", "Patterns", Network],
    ["/pareto", "Pareto / SLO", ScrollText], ["/operations", "Operations", Database],
    ["/provenance", "Provenance", Library], ["/assistant", "HR assistant", Bot],
  ] as const;
  return <div className="app-shell"><aside><div className="brand"><span>PL</span><div><strong>Policy Lab</strong><small>Architecture intelligence</small></div></div><nav aria-label="Workbench">{links.map(([to, label, Icon]) => {
    const isActive = to === "/" ? location === to : location === to || location.startsWith(`${to}/`);
    return <Link key={to} href={to} className={isActive ? "nav-link active" : "nav-link"}><Icon size={17} />{label}</Link>;
  })}</nav><footer><span className="live-dot" />Evidence workspace<small>Schema 1.0 · local artifacts</small></footer></aside><div className="workspace"><header className="topbar"><div><strong>Benchmarking</strong><span> / Decision workspace</span></div><span className="environment"><span className="live-dot" />LOCAL EVIDENCE</span></header><main><Switch>
    <Route path="/" component={Overview} /><Route path="/experiments/:id" component={ExperimentDetail} /><Route path="/experiments" component={Experiments} /><Route path="/compare" component={Compare} /><Route path="/patterns" component={Patterns} /><Route path="/pareto" component={Pareto} /><Route path="/operations" component={Operations} /><Route path="/provenance" component={Provenance} />
    <Route path="/assistant" component={ChatPage} /><Route path="/knowledge-base" component={KnowledgeBasePage} /><Route path="/about" component={AboutPage} />
  </Switch></main></div></div>;
}
