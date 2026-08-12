---
name: visa-kita-product-knowledge
description: Product, pricing, margin, market, competitor, sales, and customer-support knowledge for Visa Kita. Use for Indonesian visa product questions, e-VOA and extension packages, customer qualification, package recommendations, unit economics, marketing strategy, or positioning for Australia, China, and Malaysia.
---

# Visa Kita Product Knowledge

## Operating rules

1. Identify nationality, passport type, visit purpose, arrival date, intended stay, current location, number of travellers, and need for extension before recommending a visa.
2. Read `references/master-index.md`, then `references/knowledge-map.md`, then only the references relevant to the request.
3. Treat official immigration rules as current only as of their recorded access date. Recheck official sources before definitive eligibility, fee, processing-time, or legal statements.
4. Distinguish `official-external`, `approved-internal`, `competitor-observation`, `financial-assumption`, and `marketing-hypothesis` facts.
5. Use only `active` prices as customer offers. Current Visa Kita package proposals are `draft`; request commercial approval before quoting them as final.
6. Never guarantee approval, entry, processing time, conversion lift, or profitability. Immigration authorities retain decision authority.
7. Never describe Visa Kita as the government or an official immigration partner without documented authorization. Disclose that it is a private assistance service.
8. Never advise work under a visit visa. Escalate ambiguous purposes to a qualified immigration specialist.
9. Collect passport and financial documents only through an approved secure channel. Never claim encryption or retention controls unless verified.
10. Calculate margin with `scripts/calculate_margin.py`; never equate service fee with profit.
11. For any numeric, pricing, competitor, or packaging question, inspect the CSV tables in `data/` first. Treat them as the working source of truth for calculations and compare them against the narrative docs before answering.

## Decision flow

1. Qualify the traveller with `playbooks/customer-qualification.md`.
2. Check eligibility and product boundaries in `references/product-catalog.md`.
3. Check the price status in `pricing/price-book.md` and benefits in `pricing/packages-and-addons.md`.
4. For commercial decisions, use `pricing/unit-economics.md` and run the calculator.
5. For numeric analysis, load `data/products.csv`, `data/active-pricing.csv`, `data/unit-costs.csv`, `data/benefits.csv`, `data/competitors.csv`, and `data/assumptions.csv`.
6. For acquisition or copy, load the relevant file in `markets/` and `playbooks/marketing-strategy.md`.
7. Before making a claim, check `references/claims-and-compliance.md` and `references/source-register.md`.

## Response pattern

State the likely suitable route, why it fits, what remains to verify, government versus Visa Kita charges, included benefits, exclusions, and next safe action. State assumptions explicitly.
