#!/bin/bash
# Script to push fundmgr project to GitHub
# Make sure you've created the repository at https://github.com/satux14/fundmgr first

echo "Pushing fundmgr to GitHub..."

# Check if remote exists
if git remote get-url origin > /dev/null 2>&1; then
    echo "Remote 'origin' already configured"
else
    echo "Adding remote 'origin'..."
    git remote add origin https://github.com/satux14/fundmgr.git
fi

# Push to GitHub
echo "Pushing to GitHub..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo "✅ Successfully pushed to GitHub!"
    echo "Repository URL: https://github.com/satux14/fundmgr"
else
    echo "❌ Push failed. Make sure:"
    echo "   1. Repository exists at https://github.com/satux14/fundmgr"
    echo "   2. You have push access to the repository"
    echo "   3. You're authenticated with GitHub"
fi

