# Contributing to Vault Assistant

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

```bash
# Clone and set up
git clone https://github.com/alexkibler/vault-assistant.git
cd vault-assistant
cp .env.example .env
# Edit .env with your vault path
uv sync
```

## Running Tests

```bash
# Lint and type check
uv run ruff check .
uv run mypy main.py processor.py config.py --ignore-missing-imports

# Run full test suite
bash /tmp/test_capture.sh
uv run processor.py

# Check for syntax errors
uv run python -m py_compile main.py processor.py
```

## Making Changes

### Code Style

- Use `ruff format` for consistent formatting
- Follow PEP 8 naming conventions
- Type hints are encouraged but not required

### Testing Changes

If you modify categorization logic:
1. Update test cases in `TEST_CAPTURE_CASES.md` if needed
2. Run the test suite: `bash /tmp/test_capture.sh && uv run processor.py`
3. Verify results match expected categories in `CAPTURE_AUDIT_RESULTS.md`

If you modify the RAG pipeline:
1. Test with the queries in `TEST_CASES.md`
2. Verify sources are relevant and answers are accurate

### Commit Messages

Use clear, descriptive commit messages:
```
Fix categorization of work meeting notes
- Reorder decision tree to check for meetings before infrastructure docs
- Add explicit examples to distinguish meeting notes from documentation
```

### Pull Requests

1. Create a branch: `git checkout -b fix/your-change`
2. Make your changes and commit
3. Push: `git push origin fix/your-change`
4. Open a PR with a clear description

GitHub Actions will automatically run lint and type checks.

## Areas for Contribution

### High Priority
- [ ] Improve categorization accuracy for edge cases
- [ ] Add more comprehensive test cases
- [ ] Optimize embedding and retrieval performance
- [ ] Add support for additional note formats

### Medium Priority
- [ ] Web UI for query and capture
- [ ] Integration with other note apps
- [ ] Multi-language support
- [ ] Custom embedding model fine-tuning

### Low Priority
- [ ] Duplicate detection and merging
- [ ] Full-text search fallback
- [ ] Note linking and backlinks
- [ ] Tag inference and auto-tagging

## Questions?

Open an issue or start a discussion in the repository.
