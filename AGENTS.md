# Agent Instructions

This document provides guidelines for AI agents contributing to this repository.

## Commit Messages

**REQUIRED:** Use [Conventional Commits](https://www.conventionalcommits.org/) format for all commits.

### Format
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only changes
- `refactor:` - Code refactoring without feature changes
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks, dependencies, etc.
- `perf:` - Performance improvements
- `style:` - Code style changes (formatting, etc.)

### Examples
```bash
feat: add vacation mode switch entity
fix: correct room number extraction from entity_id
docs: update README with new configuration options
refactor: simplify controller rule evaluation
test: add tests for discovery module
chore: update Home Assistant to 2024.12
```

### Breaking Changes
For breaking changes, use `!` or add `BREAKING CHANGE:` in footer:
```bash
feat!: change entity naming scheme to include controller prefix

BREAKING CHANGE: All entity names now include "Controller" prefix
```

### Commit Strategy

**REQUIRED:** Commit in reasonable, logical steps:

- ✅ **Small, focused commits** - Each commit should represent one logical change
- ✅ **Working state** - Each commit should leave the code in a working state
- ✅ **Logical grouping** - Group related changes together
- ❌ **Avoid mixing** - Don't mix feature work with refactoring in one commit
- ❌ **Avoid WIP commits** - Don't commit half-finished work

**Examples of good commit boundaries:**
```bash
# Good: Each commit is one logical change
feat: add vacation mode switch
feat: add vacation mode to controller rules
docs: document vacation mode configuration

# Bad: Everything in one commit
feat: add complete vacation mode feature with docs
```

### Git Workflow

**Before pushing:**
- Use `git rebase -i` to clean up commit history
- Use `git commit --amend` to fix recent commits
- Squash related commits that should be one
- Reorder commits to create logical flow
- Fix commit messages for clarity

**After pushing:**
- ❌ **Never rebase or amend** - Other developers may have pulled your commits
- ✅ Use new commits to fix issues

**Commands:**
```bash
# Amend last commit (before pushing)
git commit --amend

# Interactive rebase last 3 commits (before pushing)
git rebase -i HEAD~3

# Check if branch has been pushed
git branch -vv

# Check remote status
git fetch && git status
```

## Documentation

**REQUIRED:** Keep README.md up to date with any changes that affect:
- Installation instructions
- Configuration options
- Entity names or structure
- Features or capabilities
- Usage examples

### When to update README:
- ✅ After adding new configuration options
- ✅ After adding/removing entities
- ✅ After changing entity names or structure
- ✅ After adding new features
- ✅ After changing setup flow
- ❌ For internal refactoring that doesn't affect users
- ❌ For bug fixes that don't change behavior

## Code Style

- Follow Home Assistant [development guidelines](https://developers.home-assistant.io/)
- Use type hints for all functions and methods
- Add docstrings to classes and public methods
- Keep imports organized (stdlib, third-party, local)
- Use meaningful variable names
- Prefer explicit over implicit

## Testing

- Run existing tests before committing: `make test`
- Add tests for new features
- Test in Docker environment: `make dev-up`
- Verify config flow in test instance

## Pull Requests

If creating PRs:
- Use descriptive titles following conventional commit format
- Reference related issues
- Include screenshots for UI changes
- Update CHANGELOG.md if present
