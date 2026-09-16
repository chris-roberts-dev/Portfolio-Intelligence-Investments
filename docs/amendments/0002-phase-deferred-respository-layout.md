# Amendment 0002 — Phase-Deferred Repository Layout

**Status:** NORMATIVE  
**Applies to:** `docs/dev-guide.md` Sections 5.1, 5.2, 23.2, and 24  
**Effective:** Upon adoption  
**Scope:** Repository-layout interpretation only

## 1. Purpose

Section 5.1 defines the normative target repository architecture for Portfolio Intelligence. Section 24 separately defines a normative phased implementation order and prohibits implementation of later-phase functionality before its ordered phase unless the development guide is deliberately amended.

This amendment resolves the interpretation of those requirements for release gates that occur before the complete target architecture has been implemented.

## 2. Normative clarification

The repository tree in Section 5.1 SHALL be interpreted as the **normative target architecture of the completed applicable product phases**, not as a requirement that every later-phase directory, module, worker, or implementation artifact exist before its corresponding Section 24 phase begins.

A release MAY satisfy the repository-structure requirement in Section 23.2 when all of the following are true:

1. every directory, module, configuration file, test category, and infrastructure component required by the phases completed through that release exists where applicable;
2. the implemented repository continues to obey the dependency-direction rules in Section 5.2;
3. omission of a Section 5.1 path is solely because that path belongs exclusively to a later Section 24 phase;
4. no earlier-phase implementation is placed in an architecturally incompatible location merely because the final target directory does not yet exist;
5. later-phase directories are created when their corresponding functionality is actually implemented.

The absence of a later-phase-only path SHALL NOT, by itself, block an earlier release gate.

## 3. Phase-deferred examples

For `v0.1.0 — Portfolio Analytics`, paths whose sole purpose belongs to later phases are phase-deferred.

This includes, where they have no Phase 0–4 responsibility:

- `backend/apps/optimization/`;
- `backend/apps/backtesting/`;
- `backend/portfolio_engine/optimization/`;
- `backend/portfolio_engine/rebalancing/`;
- `backend/portfolio_engine/backtesting/`;
- `backend/portfolio_engine/strategies/`;
- Celery task modules or worker configuration used only for computationally heavy later-phase optimization or backtesting workflows.

Their absence before the corresponding Section 24 phase does not constitute a Section 23.2 repository-structure failure.

This amendment does not require those exact paths to remain absent if an earlier implemented responsibility legitimately requires them.

## 4. Dependency rules remain unchanged

This amendment does **not** modify Section 5.2.

The following dependency boundaries remain normative:

```text
frontend
   ↓ HTTP
DRF views / serializers
   ↓
application services
   ↓              ↘
Django ORM         portfolio_engine
   ↓
provider adapters / infrastructure
```

The quantitative engine remains framework-independent.

No later-phase placeholder module may be introduced in a way that creates a forbidden dependency, bypasses application-service orchestration, or places financial logic in the presentation layer.

## 5. No authorization to advance later phases

This amendment is an interpretation of repository-layout timing only.

It does **not** authorize implementation before the applicable Section 24 phase of:

- portfolio optimization;
- efficient-frontier generation;
- target-allocation optimization;
- rebalancing;
- simulated rebalance trades;
- backtesting;
- strategy implementations;
- asynchronous Celery workers whose only purpose is later-phase computational work;
- AI insight functionality.

The Section 24 implementation order remains authoritative.

## 6. Section 23.2 interpretation

For Section 23.2:

> repository structure conforms to Section 5

means that the repository SHALL conform to the portion of the Section 5 target architecture required by all phases completed through the release being evaluated, while preserving the Section 5.2 dependency rules and the future architectural placement defined by Section 5.1.

A release MUST NOT create empty or nonfunctional later-phase scaffolding solely to satisfy the visual completeness of the Section 5.1 tree.

## 7. Effect on Phase 4 / v0.1.0

For the Phase 4 exit gate and `v0.1.0 — Portfolio Analytics`, Section 23.2 SHALL evaluate repository structure against the requirements of Phases 0 through 4.

Optimization, rebalancing, backtesting, strategy, later asynchronous-compute, and AI implementation artifacts are not required for the `v0.1.0` repository-layout gate unless another Phase 0–4 requirement independently requires them.

All other Section 23.2 criteria remain unchanged.