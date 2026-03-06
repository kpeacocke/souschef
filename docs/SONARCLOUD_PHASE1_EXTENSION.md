# SonarCloud Architecture Phase 1 Extension Guide

**For:** Complete Phase 1 implementation with all existing containers  
**Date:** 2026-03-06  
**Reference:** `docs/ARCHITECTURE.md` - Dependency Matrix

## Current Status

✅ **Already Defined in SonarCloud:**
- `souschef/core`
- `souschef/parsers`
- `souschef/converters`
- `souschef/filesystem  
- `souschef/ir`

## Add These Containers to Phase 1

These containers exist in the codebase and are architecturally compliant:

### 1. souschef/storage
**Contains:** database.py, blob.py (PostgreSQL, MinIO)  
**Can depend on:** core  
**Cannot depend on:** anything else

### 2. souschef/generators
**Contains:** repo.py (Ansible repository generation)  
**Can depend on:** core, converters, ir, filesystem  
**Cannot depend on:** services, orchestrators, UI layers

### 3. souschef/ui
**Contains:** Streamlit web interface (app.py, pages/, components/)  
**Can depend on:** core, api (when created), orchestrators (when created)  
**Cannot depend on:** cli, server.py, domain logic directly

## SonarCloud UI Steps

Navigate to: https://sonarcloud.io/project/architecture?id=kpeacocke_souschef

### Step 1: Add Storage Container
1. Click "Add container"
2. Name: `souschef/storage`
3. Pattern: `souschef/storage/**`
4. Click "Add dependency" → select `souschef/core` → Save

### Step 2: Add Generators Container
1. Click "Add container"
2. Name: `souschef/generators`
3. Pattern: `souschef/generators/**`
4. Click "Add dependency" → repeat for each:
   - `souschef/core`
   - `souschef/converters`
   - `souschef/ir`
   - `souschef/filesystem`
5. Save

### Step 3: Add UI Container
1. Click "Add container"
2. Name: `souschef/ui`
3. Pattern: `souschef/ui/**`
4. Click "Add dependency" → select `souschef/core` → Save
   (Note: api and orchestrators dependencies will be added when those containers are created)

## Complete Phase 1 Dependency Matrix

After adding the 3 new containers, your SonarCloud architecture should enforce these rules:

| Container | Can Depend On |
|-----------|---------------|
| **core** | *(none - foundation layer)* |
| **storage** | core |
| **filesystem** | core |
| **ir** | core |
| **parsers** | core, filesystem, ir |
| **converters** | core, parsers, ir |
| **generators** | core, converters, ir, filesystem |
| **ui** | core |

## Verification

After saving:
1. SonarCloud will re-analyze on next commit
2. Check "Architecture" tab for violations
3. Any violations will appear as issues

Expected result: **Zero violations** (we validated locally - 100% compliant!)

## Future Growth (Phase 2 - v2.1+)

Once you complete v2.1 refactor sprint:

**Add these containers:**
- `souschef/orchestrators` (migrated from top-level assessment.py, deployment.py, ansible_upgrade.py)
- `souschef/integrations` (existing github/ + new api_clients.py)
- `souschef/cli` (consolidated CLI files)
- `souschef/benchmarking` (migrated profiling.py)

**Add when implementing v3.0 enterprise features:**
- `souschef/auth`
- `souschef/audit`
- `souschef/api`

Each with dependencies defined per the full matrix in `docs/ARCHITECTURE.md`.

---

**Reference Documentation:**
- Full dependency matrix: [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) (lines 335-365)
- Compliance validation: [ARCHITECTURE_COMPLIANCE.md](../ARCHITECTURE_COMPLIANCE.md)
- Growth guidelines: [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) (lines 550-612)

**Questions?** All rules are defined in the architectural declaration - zero ambiguity!
