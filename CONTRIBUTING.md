# Contributing to FLIP

Thank you for your interest in contributing to the Farm Lifecycle Intelligence Platform (FLIP)!

## 🛠️ Development Workflow

1. **Branching Strategy**:
   - Feature: `feat/segment-XX-short-description`
   - Bugfix: `fix/issue-description`
   - Chore/Docs: `chore/description` or `docs/description`

2. **Commit Convention**:
   We strictly follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat(api): add GraphQL subscription for farm twin`
   - `fix(pwa): resolve tile caching in offline mode`
   - `test(ml): add conformal coverage unit test`

3. **Pre-commit Checks**:
   Husky runs automatically:
   - `just lint` (Biome)
   - `just typecheck` (TypeScript + Mypy)
   - `just test` (Vitest + Pytest)

4. **Pull Requests**:
   - Ensure all CI workflows pass.
   - Requires 2 approvals before merging into `main`.
   - Merging triggers automated ArgoCD staging deployment.
