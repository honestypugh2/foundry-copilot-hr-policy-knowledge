import { Link, Route, Switch, useLocation } from "wouter";
import { useState } from "react";
import { Activity, BookText, Database, Gauge, GitCompareArrows, Moon, Network, ScanSearch, ScrollText, Sun } from "lucide-react";
import AboutPage from "./pages/AboutPage";
import { Compare, Coverage, ExperimentDetail, Experiments, Operations, Overview, Pareto, Patterns } from "./pages/BenchmarkWorkbench";
import GlossaryPage from "./pages/GlossaryPage";
import KnowledgeBasePage from "./pages/KnowledgeBasePage";

function ThemeToggle() {
  const [theme, setTheme] = useState(() => document.documentElement.getAttribute("data-theme") ?? "dark");
  const toggle = () => {
    const next = theme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("pl-theme", next);
    setTheme(next);
  };
  return <button type="button" className="theme-toggle" onClick={toggle} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`} title={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}>{theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}</button>;
}

export default function App() {
  const [location] = useLocation();
  const links = [
    ["/", "Overview", Gauge], ["/experiments", "Experiments", Activity],
    ["/compare", "Compare", GitCompareArrows], ["/patterns", "Patterns", Network],
    ["/pareto", "Pareto / SLO", ScrollText], ["/operations", "Operations", Database],
    ["/coverage", "Evidence coverage", ScanSearch], ["/glossary", "Glossary", BookText],
  ] as const;
  return <div className="app-shell"><aside><div className="brand"><span>PL</span><div><strong>Pattern Lab</strong><small>Architecture intelligence</small></div></div><nav aria-label="Workbench">{links.map(([to, label, Icon]) => {
    const isActive = to === "/" ? location === to : location === to || location.startsWith(`${to}/`);
    return <Link key={to} href={to} className={isActive ? "nav-link active" : "nav-link"}><Icon size={17} />{label}</Link>;
  })}</nav><footer><span className="live-dot" />Evidence workspace</footer></aside><div className="workspace"><header className="topbar"><div><strong>Benchmarking</strong><span> / Decision workspace</span></div><ThemeToggle /></header><main><Switch>
    <Route path="/" component={Overview} /><Route path="/experiments/:id" component={ExperimentDetail} /><Route path="/experiments" component={Experiments} /><Route path="/compare" component={Compare} /><Route path="/patterns" component={Patterns} /><Route path="/pareto" component={Pareto} /><Route path="/operations" component={Operations} /><Route path="/coverage" component={Coverage} /><Route path="/glossary" component={GlossaryPage} />
    <Route path="/knowledge-base" component={KnowledgeBasePage} /><Route path="/about" component={AboutPage} />
  </Switch></main></div></div>;
}
