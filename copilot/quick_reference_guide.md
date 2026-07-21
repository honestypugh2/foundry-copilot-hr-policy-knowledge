# Quick Reference Guide — HR Policy Glossary & Policy Map

This guide ships with the Copilot Studio agent and helps the LLM route
vernacular phrases to the correct HR policy. Keep it short — the agent
reads the whole file as a system message.

---

## HR Glossary (vernacular → formal name)

| Vernacular / Shorthand | Formal Term                     |
| ---------------------- | ------------------------------- |
| PTO                    | Paid Time Off                   |
| STD                    | Short-Term Disability           |
| LTD                    | Long-Term Disability            |
| BBP                    | Blood Borne Pathogens           |
| FMLA                   | Family and Medical Leave        |
| WC                     | Workers' Compensation           |
| EAP                    | Employee Assistance Program     |
| HRBP                   | HR Business Partner             |
| OT                     | Overtime                        |
| 401k                   | 401(k) Retirement Plan          |
| OOO                    | Out of Office                   |
| WFH                    | Work From Home                  |
| dress code             | Uniform / Non-Uniform Dress Code |
| sick leave             | Paid Time Off (PTO)             |
| vacation               | Paid Time Off (PTO)             |
| time off               | Paid Time Off (PTO)             |
| holiday pay            | Hours Worked and Pay Administration: Holiday Pay |
| probation              | Hiring: Probationary Period     |
| rehire                 | Hiring: Rehiring of Retirees    |
| pre-employment physical | Hiring: Pre-employment Medical Examinations |
| code of conduct        | Code of Ethics and Related Matters |
| ethics                 | Code of Ethics and Related Matters |

---

## Policy Number → Title Map

| Policy # | Title                                                      |
| -------- | ---------------------------------------------------------- |
| 10000    | Code of Ethics and Related Matters                         |
| 20010    | Hiring: Pre-employment Medical Examinations                |
| 20020    | Hiring: Rehiring of Retirees Without Advertising           |
| 20030    | Hiring: Probationary Period                                |
| 30010    | Hours Worked and Pay Administration: Holiday Pay           |
| 40010    | Career Path: HR Generalist                                 |
| 40020    | Career Path: Data Management (DM)                          |
| 50010    | Types of Leave: Paid Time Off (PTO)                        |
| 50020    | Types of Leave: Paid Time Off (PTO) — Part-time            |
| 50030    | Short-Term Disability                                      |
| 60010    | Operational Matters: Uniform Dress Code                    |
| 60020    | Operational Matters: Non-Uniform Dress Code                |
| 70060    | Information Technology: Acceptable Use Policy              |
| 900100   | Blood Borne Pathogens — Introduction                       |
| 900200   | Blood Borne Pathogens — Methods of Compliance              |

---

## Routing Hints for the Agent

- **Document lookup** (e.g. "where is the PTO policy", "give me the dress
  code document") → use the **Lookup** action (`lookupHRPolicyDocument`).
- **Content question** (e.g. "how many PTO hours do I accrue", "do I get
  paid for holidays") → use the **Ask HR** action (`askHRPolicy`).
- **Both** (e.g. "what's our PTO policy and where can I find it") →
  call **Ask HR** first; if no inline citation is returned, call
  **Lookup** as a follow-up.

When citing, always preserve the exact policy number and full title, e.g.
`Policy 50010 — Types of Leave: Paid Time Off (PTO)`.
