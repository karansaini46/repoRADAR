#!/bin/bash
set -e

# Helper function
farm_commit() {
    BRANCH=$1
    MSG=$2
    shift 2
    FILES=$@

    echo "Farming branch $BRANCH..."
    git checkout -b $BRANCH
    git add -f $FILES
    git commit -m "$MSG"
    git push -u origin $BRANCH || echo "Failed to push $BRANCH, continuing locally..."
    
    git checkout main
    git merge $BRANCH
    git push origin main || echo "Failed to push main, continuing locally..."
}

# 7. Frontend Config
farm_commit "chore/frontend-config" "chore: frontend next.js configuration" frontend/package.json frontend/package-lock.json frontend/tsconfig.json frontend/*.mjs frontend/*.ts frontend/Dockerfile frontend/.dockerignore frontend/README.md frontend/AGENTS.md frontend/CLAUDE.md frontend/.gitignore

# 8. Frontend UI
farm_commit "feat/frontend-ui" "feat: dashboard ui and components" frontend/src/ frontend/public/

# 9. Final Cleanup (Catch anything else)
git checkout -b "chore/final-cleanup"
git add .
git commit -m "chore: final project files and cleanup" || echo "Nothing to commit"
git push -u origin chore/final-cleanup || echo "Push failed"
git checkout main
git merge chore/final-cleanup
git push origin main || echo "Final push failed"

echo "Farming rest complete!"
