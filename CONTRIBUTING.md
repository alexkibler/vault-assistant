# Contributing to Vault Assistant

Thanks for your interest in contributing! Here's how to help.

## Getting Started

### Development Setup

```bash
git clone https://github.com/alexkibler/vault-assistant.git
cd vault-assistant
uv sync

# Start development
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8765
```

### Code Quality

All PRs must pass:

```bash
# Type checking
uv run mypy main.py processor.py llm/ollama.py --ignore-missing-imports

# Linting
uv run ruff check .

# Formatting
uv run ruff format .

# All in one
uv run ruff check . && uv run ruff format . && uv run mypy main.py processor.py --ignore-missing-imports
```

## What to Contribute

### High Priority

- **Documentation improvements** - READMEs, setup guides, examples
- **Bug fixes** - Issues marked `bug`
- **Performance improvements** - Caching, indexing, query speed
- **Categorization accuracy** - Better LLM prompts for note classification

### Medium Priority

- **New query modes** - Additional ways to search vault
- **Integration examples** - Siri Shortcuts, other tools
- **Configuration options** - Make more things user-configurable
- **Error messages** - Better help when things go wrong

### Lower Priority

- **UI improvements** - The plugin is minimal but usable
- **New integrations** - Slack, Discord, etc.
- **Advanced features** - Machine learning, clustering, etc.

## Reporting Issues

### Bug Reports

Please include:
1. **System**: macOS version, Python version, etc.
2. **Steps to reproduce**: Exact steps to trigger the bug
3. **Expected vs actual**: What should happen vs what happened
4. **Error logs**: Relevant error messages or stack traces
5. **Configuration**: Your .env settings (hide sensitive paths)

### Feature Requests

Describe:
1. **Problem**: What's the use case?
2. **Solution**: How would this work?
3. **Why**: Why is this important?
4. **Examples**: How would users use it?

## Making Changes

### 1. Create a Branch

```bash
git checkout -b fix/issue-name
# or
git checkout -b feature/feature-name
```

### 2. Make Your Changes

Keep commits focused:
```bash
git commit -m "Fix: Improve categorization for meeting notes"
git commit -m "Docs: Add troubleshooting section"
```

### 3. Test

```bash
# Test the specific change
pytest tests/test_categorization.py -v

# Test everything
uv run ruff check . && uv run mypy main.py --ignore-missing-imports
```

### 4. Update Docs

If you change behavior, update:
- `README.md` (if major)
- `docs/CONFIGURATION.md` (if config-related)
- Code docstrings (always)
- Example `.env.example` (if new variable)

### 5. Push and Open PR

```bash
git push origin fix/issue-name
```

Then open a PR on GitHub with:
- **Title**: Brief description
- **Description**: What changed and why
- **Testing**: How you tested it
- **Checklist**: Run the checklist in the PR template

## Code Style

### Python

- **Type hints**: Add types to function signatures
- **Docstrings**: Use docstrings for non-obvious functions
- **Comments**: Only for complex logic
- **Line length**: Max 120 characters (ruff default)

Example:
```python
async def query_vault(
    query_text: str,
    top_k: int = 5,
) -> dict[str, Any]:
    """Query vault with semantic search.

    Args:
        query_text: The user's question
        top_k: Number of results to return

    Returns:
        Dictionary with answer and sources
    """
    # Implementation...
```

### Commits

Good commit messages:
```
Fix: Improve categorization accuracy for meeting notes
- Add explicit domain rules for "Meeting" notes
- Reorder decision tree to check meetings before infrastructure
- Test coverage: 6/6 test cases passing

Docs: Add troubleshooting section to README
- Common errors and solutions
- Links to detailed guides

Tests: Add test for duplicate detection
- Test exact duplicates
- Test similar notes (>80% similarity)
```

## Testing

### Run Tests

```bash
# All tests
pytest tests/ -v

# Specific test
pytest tests/test_categorization.py::test_categorization_accuracy -v

# With coverage
pytest tests/ --cov=. --cov-report=html
```

### Add Tests

For new features, add tests to `tests/` directory:

```python
@pytest.mark.asyncio
async def test_new_feature():
    """Test that new feature works correctly."""
    result = await my_feature("input")
    assert result == "expected_output"
```

## Documentation

### Update These When Appropriate

- **README.md** - Major features, quick overview
- **QUICKSTART.md** - Getting started in 5 minutes
- **docs/INSTALLATION.md** - Setup for each OS
- **docs/ARCHITECTURE.md** - How things work
- **docs/CONFIGURATION.md** - All config options
- **.env.example** - New environment variables
- **Code docstrings** - How functions work

### Writing Docs

- **Be concise**: Get to the point
- **Include examples**: Show how to use it
- **Link related docs**: Help readers find context
- **Use code blocks**: Format instructions clearly

## Release Process

Maintainers only, but you should know:

```bash
# Ensure everything passes
uv run ruff check . && uv run mypy main.py --ignore-missing-imports

# Update version in manifest
# Tag release
git tag v1.0.0
git push origin v1.0.0

# GitHub Actions automatically builds and creates release
```

## Questions?

- **Setup help**: Open an issue tagged `help wanted`
- **Design questions**: Start a discussion before large PRs
- **Bug reports**: Use the bug report template
- **Feature ideas**: Use the feature request template

## Community

- **Be respectful**: This is a volunteer project
- **Assume good faith**: People are helping because they care
- **Provide context**: Help others understand your issue/PR
- **Give credit**: If you use someone else's code/idea, cite it

## Code of Conduct

- **Be welcoming** to all backgrounds and skill levels
- **Be respectful** of different opinions
- **Be patient** with newcomers
- **Focus on the code**, not the person

---

Thanks for contributing to vault-assistant! 🚀
