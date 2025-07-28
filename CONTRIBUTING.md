# Contributing to GitMesh

## Introduction

GitMesh is an open-source project under the Linux Foundation Decentralized Trust umbrella. It revolutionizes Git-based collaboration through Branch-Level Intelligence, providing contextual AI assistance and intelligent workflow orchestration. This comprehensive guide outlines how the GitMesh community can contribute to the project's development and growth.

GitMesh aims to transform how developers collaborate by integrating AI-powered insights directly into Git workflows, making version control more intelligent and developer-friendly. Whether you're fixing bugs, adding features, improving documentation, or enhancing the user experience, your contributions are valuable to our community.

## Prerequisites

### Essential Requirements

<!-- Before contributing to GitMesh, please ensure you have:

- **Git**: Installed and properly configured with your GitHub account
- **Node.js**: Version 18 or higher with npm/yarn package manager
- **GitHub Account**: With SSH keys configured for secure authentication
- **Development Environment**: VS Code or your preferred IDE
- **Basic Git Knowledge**: Understanding of Git workflows and version control concepts

### Community Participation -->

**Join the [weekly meetings](https://zoom-lfx.platform.linuxfoundation.org/meeting/96156160446?password=436922cc-9811-4e05-aa60-04f7b4679c7e) on Monday at 9 am EST time zone.**

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

## Project Structure

```
gitmesh/
├── gitmesh_backend/     # Backend API and AI services
│   ├── src/            # Source code
│   ├── tests/          # Test suites
│   └── docs/           # Backend documentation
├── gitmesh_frontend/    # Frontend application
│   ├── src/            # React/TypeScript source
│   ├── public/         # Static assets
│   └── tests/          # Frontend tests
├── docs/               # Project documentation
├── scripts/            # Build and deployment scripts
├── CONTRIBUTING.md     # This file
├── LICENSE.md          # License information
└── README.md           # Project overview
```

## GitHub Flow

### Issue Selection

**Important**: Please select a task from the [published issues](https://github.com/lfdt-gitmesh/gitmesh/issues). Contributions not addressing existing issues will not be considered. For improvement proposals, kindly attend the [Monday meetings](https://zoom-lfx.platform.linuxfoundation.org/meeting/96156160446?password=436922cc-9811-4e05-aa60-04f7b4679c7e).

### Workflow Overview

Below is the GitMesh project workflow:

**Workflow Schema:**
```
1. Fork Repository → 2. Clone Locally → 3. Create Branch → 
4. Make Changes → 5. Commit & Push → 6. Create Pull Request → 
7. Code Review → 8. Merge to dev → 9. Clean up
```

### Step-by-Step Contribution Guide

#### Step 1: Visit the GitMesh Repository

1. Open your web browser and navigate to the official GitMesh repository:
   ```
   https://github.com/lfdt-gitmesh/gitmesh
   ```

#### Step 2: Fork the Repository

1. **Locate the Fork Button**: In the top-right corner of the repository page, find and click the "Fork" button.

![fork](images/fork_repo.png)

2. **Configure Fork Settings**: 
   - **Uncheck** the "Copy the main branch only" checkbox to ensure you get all branches
   - Leave the repository name as "gitmesh" (or customize if needed)
   - Ensure the description matches the original repository
   - Click "Create fork"



3. **Verify Fork Creation**: You'll be redirected to your personal fork at:
   ```
   https://github.com/YOUR_USERNAME/gitmesh
   ```

![fork-settings](images/fork_settings.png)

#### Step 3: Clone the Repository Locally

1. **Prepare Your Development Environment**:
   - Create a new folder on your local machine for GitMesh development
   - Open the folder in VS Code or your preferred IDE
   - Open a new terminal within your IDE


2. **Copy the Repository URL**:
   - On your fork's GitHub page, click the green "Code" button
   - Ensure "HTTPS" is selected
   - Click the copy icon to copy the URL to your clipboard


3. **Clone the Repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/gitmesh.git
   ```
   
   Replace `YOUR_USERNAME` with your actual GitHub username.

![clone repo](images/clone_repo.png)

4. **Verify Cloning Success**:
   - You should see output indicating the repository was cloned successfully
   - A new `gitmesh` folder should appear in your directory

#### Step 4: Navigate to GitMesh Directory

1. **Change Directory**:
   ```bash
   cd gitmesh
   ```

![change directory](images/cd.png)

2. **Verify Repository Structure**:
   ```bash
   ls -la
   ```
   
   You should see the project structure including folders like `gitmesh_backend`, `gitmesh_frontend`, etc.

#### Step 5: Set Up Remote Upstream

1. **Add Upstream Remote**:
   ```bash
   git remote add upstream https://github.com/lfdt-gitmesh/gitmesh.git
   ```

2. **Verify Remotes**:
   ```bash
   git remote -v
   ```
   
   You should see both `origin` (your fork) and `upstream` (official repository).

*Screenshot would show: Terminal output showing both remotes configured*

#### Step 6: Check Available Branches

1. **List All Branches**:
   ```bash
   git branch -a
   ```

![list branches](images/list_branches.png)

2. **Understanding Branch Structure**:
   - `main`: Production-ready code
   - `dev`: Development integration branch
   - `remotes/origin/*`: Branches from your fork
   - `remotes/upstream/*`: Branches from the official repository

#### Step 7: Checkout Development Branch

1. **Switch to a new Branch**:
   
   If the branch doesn't exist locally:
   ```bash
   git checkout -b dev origin/dev
   ```



2. **Verify Current Branch**:
   ```bash
   git branch
   ```
   
   The current branch should be highlighted with an asterisk (*).

#### Step 8: Create Your Feature Branch

1. **Create and Switch to Feature Branch**:
   ```bash
   git checkout -b feature/your-descriptive-feature-name
   ```
   
   **Branch Naming Conventions**:
   - `feature/description` - New features
   - `bugfix/description` - Bug fixes
   - `hotfix/description` - Critical fixes
   - `docs/description` - Documentation updates
   - `refactor/description` - Code refactoring
   
   **Example**:
   ```bash
   git checkout -b feature/ai-context-suggestions
   ```


2. **Confirm New Branch Creation**:
   ```bash
   git status
   ```

![create branch](images/create_branch.png)

#### Step 9: Make Your Changes

For development setup instructions, please refer to [Readme.md](README.md).

2. **Implement Your Changes**:
   - Write your code following the project's coding standards
   - Add appropriate tests for new functionality
   - Update documentation as needed
   - Ensure your changes align with the selected issue requirements

#### Step 10: Track Your Changes

1. **Check File Status**:
   ```bash
   git status
   ```
   
   This shows:
   - Modified files (red)
   - New files (red)
   - Files ready to commit (green)

![git status](images/git_status.png)

2. **Review Changes**:
   ```bash
   git diff
   ```
   
   This displays the exact changes made to files.

#### Step 11: Stage Your Changes

1. **Add Specific Files**:
   ```bash
   git add path/to/specific/file.js
   ```
   
   Or add all changes:
   ```bash
   git add -A
   ```

*Screenshot would show: Terminal after git add command*

2. **Verify Staged Changes**:
   ```bash
   git status
   ```
   
   Files ready to commit should now appear in green.

#### Step 12: Commit Your Changes

1. **Create Signed Commit** (Required for Linux Foundation):
   ```bash
   git commit -s -m "type(scope): Brief description of changes
   
   - Detailed explanation of what was changed
   - Why the change was necessary  
   - Reference to issue number (#123)
   - Any breaking changes or special notes"
   ```

   **Important**: The `-s` flag is mandatory for Linux Foundation projects as it adds a "Signed-off-by" line.

   **Commit Message Examples**:
   ```bash
   git commit -s -m "feat(ai-engine): implement contextual branch suggestions
   
   - Add new AI service for analyzing branch context
   - Integrate with existing Git workflow detection
   - Implements functionality requested in issue #45
   - Includes comprehensive test coverage"
   ```

   ```bash
   git commit -s -m "fix(branch-parser): resolve merge conflict detection bug
   
   - Fix false positive merge conflict detection
   - Update conflict resolution algorithm
   - Resolves issue #67
   - Add regression tests to prevent future occurrences"
   ```

*Screenshot would show: Terminal after successful commit with signed-off-by line*

#### Step 13: Push to Your Fork

1. **Push Feature Branch**:
   ```bash
   git push -u origin feature/your-feature-name
   ```
   
   The `-u` flag sets up tracking between your local and remote branch.

*Screenshot would show: Terminal output showing successful push to origin*

2. **Verify Push Success**:
   - Check your GitHub fork in the browser
   - Your new branch should appear in the branch dropdown
   - Recent commits should be visible

*Screenshot would show: GitHub fork page with new branch visible*

#### Step 14: Create Pull Request

1. **Navigate to Your Fork**:
   - Go to your fork on GitHub: `https://github.com/YOUR_USERNAME/gitmesh`
   - GitHub should display a banner suggesting to create a pull request

*Screenshot would show: GitHub fork page with "Compare & pull request" button*

2. **Initiate Pull Request**:
   - Click "Compare & pull request" button
   
   Or manually:
   - Click "Pull requests" tab
   - Click "New pull request"
   - Select your feature branch as the source
   - Select `lfdt-gitmesh/gitmesh:dev` as the destination

*Screenshot would show: Pull request creation interface*

3. **Configure Pull Request Details**:
   
   **Title Format**:
   ```
   type(scope): Brief description
   ```
   
   **Required Information in Description**:
   ```markdown
   ## Description
   Brief summary of changes made and motivation behind them.
   
   ## Changes Made
   - Specific change 1
   - Specific change 2
   - Specific change 3
   
   ## Testing Completed
   - [ ] Unit tests pass locally
   - [ ] Integration tests pass
   - [ ] Manual testing completed
   - [ ] No performance regressions detected
   
   ## Related Issues
   Fixes #123
   Addresses #456
   
   ## Breaking Changes
   - List any breaking changes (if none, state "None")
   
   ## Documentation Updates
   - [ ] Code comments updated
   - [ ] API documentation updated
   - [ ] User documentation updated (if applicable)
   
   ## Screenshots/Videos
   (Include if UI changes were made)
   ```

*Screenshot would show: Pull request form with all fields filled*

4. **Submit Pull Request**:
   - Review all information for accuracy
   - Click "Create pull request"

*Screenshot would show: Successfully created pull request page*

#### Step 15: Address Review Feedback

1. **Monitor Pull Request**:
   - Watch for comments from maintainers
   - Respond to feedback promptly
   - Make requested changes in the same branch

2. **Update Pull Request**:
   If changes are needed:
   ```bash
   # Make your changes
   git add -A
   git commit -s -m "address review feedback: specific changes made"
   git push origin feature/your-feature-name
   ```
   
   The pull request will automatically update.

#### Step 16: Clean Up After Merge

1. **After Successful Merge**:
   ```bash
   git checkout dev
   git pull upstream dev
   git branch -d feature/your-feature-name  # Delete local branch
   git push origin --delete feature/your-feature-name  # Delete remote branch
   ```

*Screenshot would show: Terminal after cleanup commands*

## Code Quality Standards

### Backend Standards (gitmesh_backend)

- **Language**: Follow language-specific best practices
- **Testing**: Maintain minimum 80% code coverage
- **Documentation**: Document all public APIs with clear examples
- **Performance**: Profile code for performance impacts
- **Security**: Follow secure coding practices

### Frontend Standards (gitmesh_frontend)

- **Framework**: React with TypeScript
- **Styling**: Follow established design system
- **Accessibility**: Ensure WCAG 2.1 AA compliance
- **Performance**: Optimize bundle size and runtime performance
- **Testing**: Unit tests for components and integration tests for workflows

### General Standards

- **Code Formatting**: Use project's ESLint and Prettier configurations
- **Commit Messages**: Follow semantic commit message format
- **Documentation**: Update relevant documentation for all changes
- **Testing**: Write comprehensive tests for new functionality
- **Backwards Compatibility**: Avoid breaking changes without discussion

## Documentation Requirements

All contributions must include appropriate documentation:

- **Code Comments**: Clear, concise comments for complex logic
- **API Documentation**: Update OpenAPI/Swagger specs for API changes
- **User Documentation**: Update user guides for feature changes
- **Developer Documentation**: Update technical documentation for architectural changes

## Quality Assurance Checklist

Before submitting your pull request, ensure:

### Code Quality
- [ ] Code follows project style guidelines
- [ ] All existing tests pass locally
- [ ] New functionality includes appropriate tests
- [ ] Code coverage meets project standards
- [ ] No performance regressions introduced

### Documentation
- [ ] Code includes appropriate comments
- [ ] API documentation updated (if applicable)
- [ ] User documentation updated (if applicable)
- [ ] CHANGELOG.md updated (if applicable)

### Security and Compliance
- [ ] No security vulnerabilities introduced
- [ ] All commits are signed (DCO compliance)
- [ ] No sensitive information committed
- [ ] Licensing requirements met

### Functionality
- [ ] Feature works as described in the issue
- [ ] Edge cases considered and handled
- [ ] Error handling implemented appropriately
- [ ] User experience considerations addressed

## Issue Reporting and Feature Requests

### Bug Reports

When reporting bugs, please include:

- **Clear Title**: Descriptive summary of the issue
- **Environment**: Operating system, Node.js version, browser (if applicable)
- **Steps to Reproduce**: Detailed steps to recreate the issue
- **Expected Behavior**: What should have happened
- **Actual Behavior**: What actually happened
- **Screenshots/Logs**: Visual evidence or error logs
- **Additional Context**: Any other relevant information

### Feature Requests

For new feature proposals:

- **Use Case**: Explain the problem this feature would solve
- **Proposed Solution**: High-level description of the proposed feature
- **Alternative Solutions**: Other approaches considered
- **Implementation Notes**: Technical considerations (if any)
- **Priority**: Business impact and urgency

## Community Support and Communication

### Getting Help

- **GitHub Issues**: For bug reports and feature requests
- **GitHub Discussions**: For general questions and community discussion
- **Weekly Meetings**: For real-time collaboration and guidance
- **Documentation**: Check existing docs before asking questions

### Communication Guidelines

- **Be Respectful**: Follow the code of conduct in all interactions
- **Be Patient**: Maintainers are volunteers with other commitments
- **Be Specific**: Provide detailed information when asking questions
- **Search First**: Check existing issues and discussions before creating new ones

## Recognition and Attribution

We value all contributions to GitMesh:

- **Contributors**: Listed in the project's contributors file
- **Significant Contributions**: Highlighted in release notes
- **Community Recognition**: Acknowledged in community meetings and communications

## License and Legal

By contributing to GitMesh, you agree to:

- License your contributions under the same license as the project
- Confirm you have the right to submit the contributions
- Acknowledge the Linux Foundation Decentralized Trust legal requirements
- Comply with the Developer Certificate of Origin (DCO)

## Advanced Contribution Topics

### Release Process

GitMesh follows semantic versioning:
- **Major versions**: Breaking changes
- **Minor versions**: New features (backwards compatible)
- **Patch versions**: Bug fixes (backwards compatible)

### Performance Considerations

When contributing code that may impact performance:
- Profile your changes locally
- Include performance test results in your PR description
- Consider memory usage and computational complexity
- Test with realistic data volumes

### Security Best Practices

- Never commit sensitive information (API keys, passwords, etc.)
- Validate all user inputs
- Follow secure coding practices for your language/platform
- Report security vulnerabilities privately to maintainers

## Conclusion

Thank you for your interest in contributing to GitMesh! Your contributions help make Git collaboration more intelligent and developer-friendly. By following this guide, you ensure that your contributions can be efficiently reviewed and integrated into the project.

Remember that contributing to open source is a learning experience for everyone involved. Don't hesitate to ask questions, seek guidance, and engage with the community. Every contribution, no matter how small, makes GitMesh better for all users.

Welcome to the GitMesh community!