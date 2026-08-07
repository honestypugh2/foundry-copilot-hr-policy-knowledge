"""Adapters from runnable repository patterns to benchmark contracts."""

from src.benchmarking.adapters.agent import FoundryAgentAdapter, HostedAgentAdapter
from src.benchmarking.adapters.base import BenchmarkAdapter, InvocationResult
from src.benchmarking.adapters.copilot_import import load_copilot_studio_results
from src.benchmarking.adapters.copilot_studio import CopilotStudioAdapter
from src.benchmarking.adapters.direct_search import DirectSearchAdapter
from src.benchmarking.adapters.knowledge_base import DirectKnowledgeBaseAdapter
from src.benchmarking.adapters.pattern_c import PatternCLookupAdapter

__all__ = [
	"BenchmarkAdapter",
	"CopilotStudioAdapter",
	"DirectSearchAdapter",
	"DirectKnowledgeBaseAdapter",
	"FoundryAgentAdapter",
	"HostedAgentAdapter",
	"InvocationResult",
	"PatternCLookupAdapter",
	"load_copilot_studio_results",
]