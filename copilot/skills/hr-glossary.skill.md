---
name: hr-glossary
description: >-
  Maps employee vernacular and shorthand (PTO, STD, dress code, BBP, probation,
  rehire, etc.) to the formal HR policy names used in the knowledge base, so the
  agent searches and cites the correct policy. Use whenever a question uses
  casual HR terminology.
---

# HR Glossary Skill

A reusable, self-contained skill that normalizes casual HR terminology to the
formal policy names in the "Ask HR" knowledge base. Author it once and add it to
multiple agents.

- **Copilot Studio (new agent experience):** add as a
  [Skill](https://learn.microsoft.com/en-us/microsoft-copilot-studio/agents-experience/skills-overview)
  and export/share as Markdown.
- **Microsoft Agent Framework (1.11.0+, Skills API is stable):** place this file
  in a skills directory consumed by a `SkillsProvider`.

This mirrors the code-level glossary in
[`src/search/search_service.py`](../../src/search/search_service.py); keep the
two in sync.

## Instructions to the agent

When the user's message uses any vernacular term below, expand the query to
include the **formal policy name** before searching, and cite the policy by its
number and formal title in the answer. Do not answer from general knowledge.

## Vernacular → formal policy name

| If the user says… | Search for / cite | Typical policy |
| ----------------- | ----------------- | -------------- |
| PTO, time off, vacation | Paid Time Off | 50010 |
| part-time, part time PTO | Paid Time Off - Part-time | 50020 |
| sick leave, sick time, STD | Short-Term Disability | 50030 |
| dress code, what to wear, uniforms | Uniform Dress Code | 60010 |
| holidays, holiday pay, day off | Holiday Pay | 30010 |
| new hire, probation, onboarding | Probationary Period | 20030 |
| ethics, code of conduct | Code of Ethics | 10000 |
| rehire, re-hire, retiree | Rehiring of Retirees | 20020 |
| medical exam, physical, drug test | Pre-employment Medical Examinations | 20010 |
| blood borne, BBP, needlestick | Blood Borne Pathogens | 900100 |
| career path, promotion, advancement | Career Path | 40010 / 40020 |
| HR generalist | HR Generalist Career Path | 40010 |
| data management, DM | Data Management Career Path | 40020 |

## Behavior rules

1. If a term is ambiguous (e.g. "leave" could be PTO or Short-Term Disability),
   ask a brief clarifying question.
2. Always ground the answer in retrieved policy documents and cite
   `[Policy XXXXX - Title]`.
3. If no policy is found, use the standard refusal: "I could not find this
   information in the HR policy documents. Please contact your HR representative
   for assistance."
