#!/bin/bash
set -e

echo "🌱 Farming commits for green graph..."
echo ""

# Helper: commit specific files on main directly
farm_commit() {
    MSG=$1
    shift
    FILES="$@"

    echo "📦 Committing: $MSG"
    git add -f $FILES 2>/dev/null || true
    git commit -m "$MSG" --allow-empty 2>/dev/null || echo "  ⚠️  Nothing to commit for: $MSG"
}

# ─── Commit 1: Backend settings & config updates ───
farm_commit "feat(config): add system settings and update dependencies" \
    autoscan/shared/settings.py \
    autoscan/settings.json \
    requirements.txt \
    docker-compose.yml

# ─── Commit 2: Orchestration scheduler improvements ───
farm_commit "feat(orchestration): enhance scheduler with auto-mode support" \
    autoscan/orchestration/scheduler.py \
    autoscan/orchestration/__init__.py

# ─── Commit 3: Queue manager for pipeline processing ───
farm_commit "feat(orchestration): add queue manager for pipeline processing" \
    autoscan/orchestration/queue_manager.py

# ─── Commit 4: AI layer verifier and batch processor updates ───
farm_commit "feat(ai): update verifier and batch processor for multi-key rotation" \
    autoscan/ai_layer/verifier.py \
    autoscan/ai_layer/batch_processor.py

# ─── Commit 5: Cloning pipeline improvements ───
farm_commit "fix(cloning): improve pipeline reliability and error handling" \
    autoscan/cloning/pipeline.py

# ─── Commit 6: API main and system routes ───
farm_commit "feat(api): add system routes and update api entrypoint" \
    autoscan/api/main.py \
    autoscan/api/routes/system.py \
    autoscan/api/routes/__init__.py

# ─── Commit 7: Companies API and dashboard route ───
farm_commit "feat(api): enhance companies endpoint and dashboard analytics" \
    autoscan/api/routes/companies.py \
    autoscan/api/routes/dashboard.py

# ─── Commit 8: Run all and utility scripts ───
farm_commit "feat(backend): add run_all orchestrator and utility scripts" \
    autoscan/run_all.py \
    check_db.py \
    autoscan/test_keys.py \
    test_keys.py

# ─── Commit 9: Dashboard logs page ───
farm_commit "feat(frontend): add pipeline logs page to dashboard" \
    frontend/src/app/dashboard/logs/page.tsx

# ─── Commit 10: Dashboard UI updates ───
farm_commit "feat(frontend): update dashboard page with auto-mode controls" \
    frontend/src/app/dashboard/page.tsx

# ─── Commit 11: Dashboard layout update ───
farm_commit "feat(frontend): update dashboard layout with verified findings nav" \
    frontend/src/app/dashboard/layout.tsx

# ─── Commit 12: Verified findings page ───
farm_commit "feat(frontend): add verified findings dashboard page" \
    frontend/src/app/dashboard/verified/page.tsx

# ─── Commit 13: Tests ───
farm_commit "test: add ai layer unit tests" \
    tests/test_ai_layer.py

# ─── Commit 14: Final cleanup - catch anything remaining ───
git add . 2>/dev/null || true
git diff --cached --quiet || git commit -m "chore: cleanup scripts and minor fixes"

echo ""
echo "✅ All commits created! Pushing to origin..."
git push origin main

echo ""
echo "🎉 Done! Your git graph is about to be green 💚"
