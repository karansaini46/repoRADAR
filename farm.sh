#!/bin/bash

# Exit on error
set -e

echo "Initializing Git repository..."
git init -b main
git remote add origin https://github.com/karansaini46/repoRADAR.git

echo "Creating .gitignore..."
cat << 'EOF' > .gitignore
venv/
__pycache__/
*.pyc
.env
autoscan.db
postgres_data/
reports_data/
frontend/node_modules/
frontend/.next/
EOF

# Initial commit on main to anchor the repository
git add .gitignore
git commit -m "chore: initial repository anchor"
git push -u origin main || echo "Failed to push main initially, continuing..."

# Helper function to create branch, commit, push, and merge
farm_commit() {
    BRANCH=$1
    MSG=$2
    shift 2
    FILES=$@

    echo "Farming branch $BRANCH..."
    git checkout -b $BRANCH
    git add $FILES
    git commit -m "$MSG"
    
    # Try to push branch (might fail if auth is not set, we'll continue)
    git push -u origin $BRANCH || echo "Failed to push $BRANCH, continuing locally..."
    
    git checkout main
    git merge $BRANCH
    git push origin main || echo "Failed to push main, continuing locally..."
}

# 1. Initial Setup
farm_commit "chore/initial-setup" "chore: initial project configuration and docker setup" .gitignore Dockerfile docker-compose.yml nginx.conf .dockerignore .env.example requirements.txt

# 2. Backend Shared
farm_commit "feat/backend-shared" "feat: backend database and shared models" autoscan/shared/ autoscan/__init__.py init_db.py

# 3. Backend Discovery & Cloning
farm_commit "feat/backend-discovery" "feat: github discovery and cloning engines" autoscan/discovery/ autoscan/cloning/

# 4. Backend Analysis
farm_commit "feat/backend-analysis" "feat: security scanning and ai analysis layer" autoscan/scanning/ autoscan/ai_layer/ autoscan/impact/

# 5. Backend Reports & Outreach
farm_commit "feat/backend-reports-outreach" "feat: report generation and automated outreach" autoscan/reports/ autoscan/outreach/ autoscan/enrichment/

# 6. Backend Orchestration
farm_commit "feat/backend-orchestration" "feat: orchestration, api routers, and payments" autoscan/orchestration/ autoscan/api/ autoscan/payments/

# 7. Frontend Config
farm_commit "chore/frontend-config" "chore: frontend next.js configuration" frontend/package.json frontend/package-lock.json frontend/tsconfig.json frontend/*.mjs frontend/*.ts frontend/Dockerfile frontend/.dockerignore frontend/README.md frontend/AGENTS.md frontend/CLAUDE.md

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

echo "Farming complete!"
