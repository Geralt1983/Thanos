# Contributing to Thanos

Thank you for contributing to Thanos! This guide will help you maintain code quality and consistency.

## Code Quality and Linting

This project uses [Ruff](https://docs.astral.sh/ruff/) for Python code linting and formatting. Ruff is a fast, modern linter that replaces multiple tools (flake8, isort, pyupgrade, pydocstyle) with a single, performant solution.

### Installing Ruff

Before contributing, install Ruff in your development environment:

```bash
# Option 1: Install in your virtual environment (recommended)
pip install -r requirements-dev.txt

# Option 2: Install via pip directly
pip install 'ruff>=0.1.0'

# Option 3: Install globally with pipx
pipx install ruff

# Option 4: Install via homebrew (macOS)
brew install ruff
```

### Linting Commands

Use these commands to check and fix your code before committing:

#### Check for Linting Issues

```bash
# Check all Python files for linting violations
ruff check .

# Check a specific file or directory
ruff check ./Tools/
ruff check ./commands/pa/tasks.py
```

This command will report all linting violations including:
- Code errors (undefined variables, unused imports)
- Style violations (line length, quote style)
- Best practice warnings (complexity, naming conventions)
- Missing or malformatted docstrings

#### Auto-Fix Linting Issues

```bash
# Automatically fix all auto-fixable violations
ruff check --fix .

# Fix issues in a specific file or directory
ruff check --fix ./Tools/
```

Auto-fixable issues include:
- Import sorting and organization
- Unused import removal
- Quote style normalization
- Trailing whitespace removal
- Missing trailing commas
- Line spacing normalization

**Note:** Some issues require manual fixes (e.g., line length, docstrings, naming conventions).

#### Format Code

```bash
# Format all Python files with consistent style
ruff format .

# Format a specific file or directory
ruff format ./Tools/
```

The formatter applies Black-compatible formatting:
- Double quotes for strings
- Space indentation (4 spaces)
- Line length of 100 characters
- Consistent spacing and line breaks

### Pre-Commit Workflow

#### Option 1: Automated Pre-Commit Hooks (Recommended)

Install pre-commit hooks to automatically run linting and formatting before each commit:

```bash
# Install pre-commit (included in requirements-dev.txt)
pip install pre-commit

# Install git hooks
pre-commit install

# (Optional) Run on all files to test
pre-commit run --all-files
```

Once installed, pre-commit will automatically:
1. Run `ruff check --fix` to auto-fix linting issues
2. Run `ruff format` to format code consistently
3. Block the commit if any issues can't be auto-fixed

To bypass hooks temporarily (not recommended):
```bash
git commit --no-verify
```

#### Option 2: Manual Pre-Commit Workflow

**Before committing any code, always run:**

```bash
# Step 1: Auto-fix linting issues
ruff check --fix .

# Step 2: Format code
ruff format .

# Step 3: Verify no violations remain
ruff check .

# Step 4: Run tests (if applicable)
pytest
```

If `ruff check .` shows any remaining violations, fix them manually before committing.

### Configuration

Linting configuration is defined in `pyproject.toml` under the `[tool.ruff]` and `[tool.ruff.lint]` sections:

- **Line length:** 100 characters
- **Target Python version:** 3.9+
- **Quote style:** Double quotes
- **Enabled rules:** F (pyflakes), E/W (pycodestyle), I (isort), N (naming), D (docstrings), UP (pyupgrade), B (bugbear), C4 (comprehensions), T20 (print), RET (return), SIM (simplify), PTH (pathlib), ARG (unused arguments)

Excluded directories are listed in `.ruffignore`:
- `.auto-claude/`, `.git/`, `venv/`, `__pycache__/`
- Build artifacts, cache directories, IDE files
- Project-specific directories (.swarm/, .hive-mind/, memory/)

### Common Linting Issues and How to Fix Them

#### Unused Imports (F401)
```python
# ❌ Bad
from typing import Dict, List
def foo() -> str:  # Dict and List are unused
    return "bar"

# ✅ Good
def foo() -> str:
    return "bar"
```

#### Unused Variables (F841)
```python
# ❌ Bad
result = expensive_operation()
return success  # result is unused

# ✅ Good
_ = expensive_operation()  # Use _ for intentionally unused
return success
```

#### Line Too Long (E501)
```python
# ❌ Bad
def process_data(param1, param2, param3, param4, param5, param6, param7, param8):
    pass

# ✅ Good
def process_data(
    param1,
    param2,
    param3,
    param4,
    param5,
    param6,
    param7,
    param8,
):
    pass
```

#### Missing Docstrings (D102, D103)
```python
# ❌ Bad
def complex_function(data):
    return data.process()

# ✅ Good
def complex_function(data):
    """Process the input data using the configured processor.

    Args:
        data: The data object to process.

    Returns:
        The processed result.
    """
    return data.process()
```

#### Import Sorting (I001)
```python
# ❌ Bad (unsorted imports)
from pathlib import Path
import sys
from typing import Dict
import os

# ✅ Good (sorted: stdlib, third-party, local)
import os
import sys
from pathlib import Path
from typing import Dict
```

### Intentional Violations

If you need to intentionally violate a rule (rarely needed), use inline comments:

```python
# Ignore a specific rule on one line
result = eval(user_input)  # noqa: S307

# Ignore multiple rules on one line
long_line = "very " * 50 + "long string"  # noqa: E501, S001

# Ignore all rules on one line (use sparingly)
complex_code()  # noqa
```

**Important:** Only use `noqa` when absolutely necessary and document why in a comment.

### IDE Integration

Configure your IDE to run Ruff automatically:

#### VS Code
Install the [Ruff extension](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff) and add to `settings.json`:
```json
{
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll": true,
      "source.organizeImports": true
    }
  }
}
```

#### PyCharm
Configure Ruff as an external tool or use the [Ruff plugin](https://plugins.jetbrains.com/plugin/20574-ruff).

#### Vim/Neovim
Use ALE, Syntastic, or nvim-lspconfig with ruff-lsp.

### Running Tests

Always run the test suite after making changes:

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=.

# Run specific test file
pytest tests/unit/test_command_router.py
```

### Questions?

If you encounter linting issues you can't resolve:
1. Check the [Ruff documentation](https://docs.astral.sh/ruff/)
2. Review the rule explanation: `ruff rule <CODE>` (e.g., `ruff rule F401`)
3. Check existing code for patterns
4. Ask for help in your pull request

## Pull Request Guidelines

When submitting a pull request:

1. ✅ **All linting checks pass:** `ruff check .` returns no errors
2. ✅ **Code is formatted:** `ruff format .` applied
3. ✅ **Tests pass:** `pytest` completes successfully
4. ✅ **No debugging code:** Remove print statements, console.logs
5. ✅ **Descriptive commit messages:** Explain what and why
6. ✅ **Documentation updated:** If adding features, update relevant docs

## Code Style Guidelines

### General Principles

- **Readability over cleverness:** Write code that's easy to understand
- **Explicit is better than implicit:** Be clear about what your code does
- **DRY (Don't Repeat Yourself):** Extract common patterns into functions
- **Single Responsibility:** Each function/class should do one thing well
- **Type hints:** Use type annotations for function signatures
- **Docstrings:** Document all public functions, classes, and modules

### Python-Specific

- **Line length:** 100 characters maximum
- **Indentation:** 4 spaces (no tabs)
- **Quotes:** Double quotes for strings
- **Imports:** Sorted by stdlib, third-party, local
- **Naming:**
  - `snake_case` for functions and variables
  - `PascalCase` for classes
  - `UPPER_CASE` for constants
  - Descriptive names over abbreviations

### Example

```python
"""Module for processing user data.

This module provides utilities for validating and transforming
user input data before storage.
"""

from typing import Dict, List, Optional
import re

from external_library import ExternalValidator


class UserDataProcessor:
    """Process and validate user data.

    Attributes:
        validator: The external validator instance.
        max_retries: Maximum number of validation retries.
    """

    MAX_FIELD_LENGTH = 255  # Constant in UPPER_CASE

    def __init__(self, validator: ExternalValidator, max_retries: int = 3):
        """Initialize the processor.

        Args:
            validator: The external validator to use.
            max_retries: Maximum number of retries for validation.
        """
        self.validator = validator
        self.max_retries = max_retries

    def process_user_data(
        self,
        data: Dict[str, str],
        validate: bool = True,
    ) -> Optional[Dict[str, str]]:
        """Process and optionally validate user data.

        Args:
            data: Raw user data dictionary.
            validate: Whether to validate the data.

        Returns:
            Processed data dictionary, or None if validation fails.
        """
        if validate and not self._validate_data(data):
            return None

        return self._transform_data(data)

    def _validate_data(self, data: Dict[str, str]) -> bool:
        """Validate data using the configured validator.

        Args:
            data: Data to validate.

        Returns:
            True if valid, False otherwise.
        """
        for attempt in range(self.max_retries):
            if self.validator.validate(data):
                return True
        return False

    def _transform_data(self, data: Dict[str, str]) -> Dict[str, str]:
        """Transform data to standard format.

        Args:
            data: Data to transform.

        Returns:
            Transformed data dictionary.
        """
        return {
            key.lower(): value.strip()
            for key, value in data.items()
        }
```

---

Thank you for helping maintain high code quality in the Thanos project!
