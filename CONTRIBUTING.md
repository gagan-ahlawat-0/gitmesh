# Contributing to GitMesh

## Introduction

GitMesh is an open-source project under the Linux Foundation Decentralized Trust umbrella. It revolutionizes Git-based collaboration through Branch-Level Intelligence, providing contextual AI assistance and intelligent workflow orchestration. This comprehensive guide outlines how the GitMesh community can contribute to the project's development and growth.

GitMesh aims to transform how developers collaborate by integrating AI-powered insights directly into Git workflows, making version control more intelligent and developer-friendly. Whether you're fixing bugs, adding features, improving documentation, or enhancing the user experience, your contributions are valuable to our community.

## Prerequisites

### Essential Requirements

**Join the weekly meetings on Wednesday at 1 pm UTC time zone.**

These meetings are essential for:
- Understanding project roadmap and priorities
- Discussing implementation approaches
- Getting guidance on complex contributions
- Coordinating with other contributors
- Staying updated on project developments

## Code of Conduct and Legal Requirements

As a Linux Foundation Decentralized Trust project, GitMesh adheres to strict community standards:

- [Linux Foundation Privacy Policy](https://www.linuxfoundation.org/legal/privacy-policy)
- [Terms of Use](https://www.linuxfoundation.org/legal/terms)
- [Antitrust Policy](https://www.linuxfoundation.org/legal/antitrust-policy)
- [Code of Conduct](https://www.lfdecentralizedtrust.org/code-of-conduct)

Please review and understand these policies before contributing.


### Issue Selection

**Important**: Please select a task from the [published issues](https://github.com/LF-Decentralized-Trust-Mentorships/gitmesh/issues). Contributions not addressing existing issues will not be considered. For improvement proposals, kindly attend the Wednesday meetings.

### Workflow Overview

Below is the GitMesh project workflow:

**Workflow Schema:**
```
1. Fork Repository → 2. Clone Locally → 3. Create Branch → 
4. Make Changes → 5. Commit & Push → 6. Create Pull Request → 
7. Code Review → 8. Merge to dev → 9. Clean up
```

## Step-by-Step Contribution Guide

Follow these steps to contribute effectively to the GitMesh project.

### 1. Fork the Repository

Click the **Fork** button on the top-right of the [main repository](https://github.com/LF-Decentralized-Trust-Mentorships/gitmesh) to create your own copy.

### 2. Clone Your Fork

Clone your forked repository to your local system:
```bash
git clone https://github.com/<your-username>/gitmesh.git
cd gitmesh
```

### 3. Add Upstream Remote

Link your local repository with the original repository to stay updated:
```bash
git remote add upstream https://github.com/LF-Decentralized-Trust-Mentorships/gitmesh.git
```

**Why add upstream?**  
This lets you sync your fork with the latest changes from the main repository instead of reforking every time.

### 4. Keep Your Fork Updated

#### **When Starting Fresh (No Local Changes)**

Always pull the latest updates before starting new work:
```bash
git fetch upstream
git merge upstream/main
```

This ensures your local repository stays current with the main branch.

#### **When You Have Local Changes**

If you've made changes locally and need to sync with the latest updates:

**Step 1: Save Your Local Changes**
```bash
git stash
```

**Step 2: Pull Latest Updates**
```bash
git fetch upstream
git merge upstream/main
```

**Step 3: Update Dependencies**
```bash
pnpm install
```

**Step 4: Restore Your Local Changes**
```bash
git stash pop
```

**Note:** If there are conflicts after `git stash pop`, you'll need to resolve them manually before continuing.

 **Best Practice:** Always sync your fork before creating a new branch to minimize merge conflicts later.

### 5. Create a New Branch

Create a feature or fix branch before making changes:
```bash
git checkout -b <branch-name>
```

#### Branch Naming Conventions
- **Feature**: Use `feature/<short-description>` — Example: `feature/add-ai-support`
- **Bug Fix**: Use `fix/<short-description>` — Example: `fix/profile-upload-error`
- **Documentation**: Use `docs/<short-description>` — Example: `docs/update-readme`
- **Enhancement**: Use `enhancement/<short-description>` — Example: `enhancement/improve-theme-colors`
- **Refactor**: Use `refactor/<short-description>` — Example: `refactor/code-cleanup`

 **Tip:** Use short, descriptive branch names in lowercase, separated by hyphens.


### 6. Make Your Changes

Implement your updates, fix issues, or add new features.

**Keep changes small and meaningful** — this makes reviews easier.

### 7. Stage and Commit Changes
```bash
git add .
git commit -s -m "Brief description of the change"
```

The `-s` flag signs your commit, confirming you agree to the Developer Certificate of Origin (DCO).

### 8. Push Your Branch to GitHub
```bash
git push origin <branch-name>
```

**Example:**
```bash
git push origin feature/add-ai-support
```
### 9. Create a Pull Request (PR)

Go to your fork on GitHub → click **Compare & Pull Request**.

Make sure:
- The base branch is `main` or `dev` (as required)
- Your PR title is clear and concise
- Description explains what and why you changed

### 10. Participate in Code Review

Maintainers may request updates. You do not need to create a new PR — just apply the changes to your existing branch and push.

If changes are needed:
```bash
# Make updates
git add .
git commit -s -m "Address review feedback"
git push origin <branch-name>
```

### 11. Sync Your Branch (If Needed)

If new commits are added to the main repository while your PR is open:
```bash
git fetch upstream
git merge upstream/main
git push origin <branch-name>
```

### 12. After Merge

Once your PR is merged:
```bash
# Switch to local main branch
git checkout main

# Update your local main with the latest upstream changes
git fetch upstream
git merge upstream/main

# Push updates to your fork
git push origin main

# Optional: Delete the merged feature branch locally to keep your repo clean
git branch -d <branch-name>

```

**Congratulations!** Your contribution is now part of GitMesh.

Don't forget to keep your fork synced before starting your next task.