#!/bin/bash
echo "=== GIT STATUS ==="
git status --porcelain
echo "=== GIT LOG ==="
git log --oneline -5
echo "=== GIT REMOTE ==="
git remote -v
echo "=== GIT BRANCH ==="
git branch
echo "=== DONE ==="
