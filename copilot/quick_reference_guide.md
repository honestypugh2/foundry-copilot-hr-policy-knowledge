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
| 31000    | Code of Ethics and Related Matters                         |
| 50410    | Hiring: Pre-employment Medical Examinations                |
| 50435    | Hiring: Rehiring of Retirees Without Advertising           |
| 50455    | Hiring: Probationary Period                                |
| 50715    | Hours Worked and Pay Administration: Holiday Pay           |
| 50815    | Career Path: HR Generalist                                 |
| 50855    | Career Path: Data Management (DM)                          |
| 51350    | Types of Leave: Paid Time Off (PTO)                        |
| 51355    | Types of Leave: Paid Time Off (PTO) — Part-time            |
| 51370    | Short-Term Disability                                      |
| 52005    | Operational Matters: Uniform Dress Code                    |
| 52010    | Operational Matters: Non-Uniform Dress Code                |
| 87100    | Information Technology: Acceptable Use Policy              |
| 101100   | Blood Borne Pathogens — Introduction                       |
| 101205   | Blood Borne Pathogens — Methods of Compliance              |

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
`Policy 51350 — Types of Leave: Paid Time Off (PTO)`.
