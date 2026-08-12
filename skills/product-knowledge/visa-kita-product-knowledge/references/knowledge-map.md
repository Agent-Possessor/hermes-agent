# Knowledge Map

Primary navigation lives in `references/master-index.md`. Use this file as the deeper map once the overall structure is clear.

- Product identity and scope: `references/product-overview.md`
- Visa purposes, duration, official fees, and evidence: `references/product-catalog.md`
- Commercial prices, including detailed B1 VOA/e-VOA packages and extension, plus package status: `pricing/price-book.md`
- Benefits and add-ons: `pricing/packages-and-addons.md`
- Cost, CAC, margin, and LTV: `pricing/unit-economics.md`
- Competitor prices: `pricing/competitor-benchmark.md`
- Australia, China, Malaysia: corresponding file under `markets/`
- Qualification and product selection: `playbooks/customer-qualification.md` and `playbooks/package-recommendation.md`
- Marketing experiments: `playbooks/marketing-strategy.md`
- Customer-facing answers and objections: `playbooks/sales-and-objections.md`
- Claim safety and privacy: `references/claims-and-compliance.md`
- Source provenance and freshness: `references/source-register.md`

Raw numeric tables:

- `data/products.csv` for product scope and approved-internal pricing
- `data/active-pricing.csv` for package prices and status
- `data/unit-costs.csv` for government, levy, payment, CS, and operations cost assumptions
- `data/benefits.csv` for package inclusions and evidence status
- `data/competitors.csv` for observed competitor offers
- `data/assumptions.csv` for unvalidated model assumptions

For numeric analysis, inspect `data/*.csv` and run `scripts/calculate_margin.py`. Do not infer an active customer offer from a draft model.
