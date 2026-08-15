# Documentation Map

Start with [Build the Retrieval Patterns](patterns/README.md). It is the linear
setup path: Pattern A and its options first, followed by one focused guide each
for A2, B, C, and Hosted.

The top-level [README](../README.md) is the repository front door. Documents
below are focused deep dives; they should not redefine pattern names or provide
competing setup flows.

## Build and run

| Document | Use it for |
| --- | --- |
| [patterns/README.md](patterns/README.md) | **Start here.** Ordered, one-pattern-at-a-time build and validation guides. |
| [PatternSetupAndBenchmarkGuide.md](PatternSetupAndBenchmarkGuide.md) | File ownership, smoke-test boundaries, and benchmark entry points after setup. |
| [Walkthrough.md](Walkthrough.md) | Linear environment provisioning and first-run sequence. |
| [RetrievalPatterns.md](RetrievalPatterns.md) | Conceptual decision tree and architecture comparison. |
| [DataPipelineAndTesting.md](DataPipelineAndTesting.md) | Indexing options, resource creation, schemas, and ingestion validation. |
| [CopilotStudioIntegration.md](CopilotStudioIntegration.md) | Interactive Copilot Studio wiring for A, A2, B, and Hosted. |
| [CopilotStudioLookupRouting.md](CopilotStudioLookupRouting.md) | Pattern C REST tool and routing rules. |
| [CopilotStudioHybridExample.md](CopilotStudioHybridExample.md) | Combining answer and locator paths in one Copilot. |
| [CopilotStudioTestingGuide.md](CopilotStudioTestingGuide.md) | End-to-end validation and corpus-grounded query catalog. |

## Architecture deep dives

| Document | Scope |
| --- | --- |
| [FoundryAgentArchitecture.md](FoundryAgentArchitecture.md) | Pattern B KB, MCP connection, PromptAgent, and forced retrieval. |
| [AgentArchitecturePaths.md](AgentArchitecturePaths.md) | Managed Foundry Agent Service versus hosted Agent Framework runtime. |
| [SharePointLogicAppsArchitecture.md](SharePointLogicAppsArchitecture.md) | Alternative SharePoint/Logic Apps ingestion architecture. |
| [Distribution-M365-Teams.md](Distribution-M365-Teams.md) | Distribution after a retrieval pattern is working. |
| [LabCoverage.md](LabCoverage.md) | Crosswalk to the Azure/Copilot-Studio-and-Azure labs. |

## Benchmarking

| Document | Scope |
| --- | --- |
| [PatternSetupAndBenchmarkGuide.md](PatternSetupAndBenchmarkGuide.md) | Benchmark boundaries, code ownership, and comparison entry points. |
| [CopilotStudioBenchmarking.md](CopilotStudioBenchmarking.md) | Configure five isolated pattern agents and run Direct Line comparisons. |
| [BenchmarkingDecisionSystem.md](BenchmarkingDecisionSystem.md) | The evidence system: rules, workbench, gates, cost lanes, and roadmap. |
| [ReuseForYourUseCase.md](ReuseForYourUseCase.md) | Fork the benchmark for another RAG/agent use case (~80% reusable). |
| [BenchmarkLoadTesting.md](BenchmarkLoadTesting.md) | Capacity/load experiments kept separate from controlled runs. |

## Published article

The canonical architecture article is
[Grounding Copilot Studio Agents with Azure AI Search and Foundry IQ](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/grounding-copilot-studio-agents-with-azure-ai-search-and-foundry-iq/4539337).
It defines the five pattern names used by this repository. The benchmark guides
evaluate those patterns; they do not rename or replace them.