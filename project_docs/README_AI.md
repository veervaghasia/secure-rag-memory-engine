# README_AI.md

# AI Navigation Guide

This repository follows an architecture-first development process. Before suggesting implementations, understand the current project state by consulting the documents below.

---

# Document Order

Always use documents in the following priority.

1. `00_ARCHITECTURE.md`
2. `02_DECISIONS.md`
3. `06_DEPENDENCIES.md`
4. `04_CURRENT_STATE.md`
5. `03_CODEBASE.md`
6. `05_TECH_DEBT.md`
7. `01_ROADMAP.md`
8. `07_RUNTIME_FLOW.md`

---

# Purpose of Each Document

## 00_ARCHITECTURE.md

Defines the permanent architecture.

Contains:

* architectural manifestos
* architectural pillars
* responsibilities of each pillar
* phase organizations
* confirmed architectural decisions

Do not suggest designs that violate this document.

---

## 01_ROADMAP.md

Defines the implementation plan.

Use it to determine

* what phase is active
* branch order
* implementation milestones
* future work

Do not implement future roadmap items unless explicitly requested.

---

## 02_DECISIONS.md

Contains Architectural Decision Records (ADRs).

Before proposing alternative implementations, verify whether the decision has already been made.

If a suggestion conflicts with an accepted decision, explain the trade-off rather than silently replacing it.

---

## 03_CODEBASE.md

Automatically generated.

Represents the current public interfaces of the codebase.

Never assume functions or classes exist if they are absent here.

---

## 04_CURRENT_STATE.md

Represents implementation progress.

Use it to determine

* completed branches
* active branch
* remaining work
* known implementation status

Treat this as the source of truth for project progress.

---

## 05_TECH_DEBT.md

Lists intentionally deferred work.

Do not recommend implementing items recorded here unless explicitly requested.

---

## 06_DEPENDENCIES.md

Defines implementation prerequisites.

Before modifying multiple modules, verify that dependency order is respected.

If a requested task depends on unfinished work, explain the dependency before writing code.

---

## 07_RUNTIME_FLOW.md

Describes runtime execution.

Use it to understand how requests move through the system.

Do not change runtime behavior unless requested.

---

# General Rules

* Respect the architectural manifestos.
* Do not introduce LangChain or LlamaIndex into business logic.
* Prefer extending existing abstractions over creating parallel implementations.
* Minimize changes outside the active branch.
* Preserve stable public interfaces whenever possible.
* Explain architectural conflicts before generating code.

---

# Branch Workflow

When working on a branch:

1. Read the architecture.
2. Read the decisions.
3. Read dependencies.
4. Read current implementation state.
5. Read the codebase map.
6. Implement only the requested branch.
7. Do not modify unrelated modules.

After the branch is complete, perform an architectural review before considering the work finished.

---

# If Information Is Missing

Never invent architecture.

Instead, explicitly ask for clarification or explain what additional information is required.
