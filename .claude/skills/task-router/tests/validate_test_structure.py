#!/usr/bin/env python3
"""
Validate test structure without running pytest.
Checks imports, class definitions, and method signatures.
"""

import ast
import sys
from pathlib import Path

def validate_test_file(file_path):
    """Validate test file structure."""
    print(f"Validating: {file_path}")
    print("=" * 70)

    # Read and parse the file
    try:
        with open(file_path, 'r') as f:
            content = f.read()

        tree = ast.parse(content, filename=str(file_path))
        print("✅ Syntax valid")
    except SyntaxError as e:
        print(f"❌ Syntax error: {e}")
        return False

    # Check for required imports
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module)

    required_imports = ['pytest', 'asyncio', 'unittest.mock', 'pathlib', 'sys']
    for req in required_imports:
        if any(req in imp for imp in imports if imp):
            print(f"✅ Import: {req}")
        else:
            print(f"⚠️  Missing import: {req}")

    # Check for test classes
    test_classes = []
    test_methods = []
    fixtures = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if node.name.startswith('Test'):
                test_classes.append(node.name)
        elif isinstance(node, ast.FunctionDef):
            if node.name.startswith('test_'):
                test_methods.append(node.name)
            # Check for fixture decorator
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Name) and decorator.id == 'fixture':
                    fixtures.append(node.name)
                elif isinstance(decorator, ast.Attribute) and decorator.attr == 'fixture':
                    fixtures.append(node.name)

    print(f"\n✅ Test classes: {len(test_classes)}")
    for cls in test_classes[:5]:  # Show first 5
        print(f"   - {cls}")
    if len(test_classes) > 5:
        print(f"   ... and {len(test_classes) - 5} more")

    print(f"\n✅ Test methods: {len(test_methods)}")
    for method in test_methods[:5]:  # Show first 5
        print(f"   - {method}")
    if len(test_methods) > 5:
        print(f"   ... and {len(test_methods) - 5} more")

    print(f"\n✅ Fixtures: {len(fixtures)}")
    for fixture in fixtures:
        print(f"   - {fixture}")

    # Check for async tests
    async_tests = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith('test_'):
            async_tests += 1

    if async_tests > 0:
        print(f"\n✅ Async tests: {async_tests}")

    print("\n" + "=" * 70)
    print("✅ TEST FILE STRUCTURE VALID")
    return True

if __name__ == "__main__":
    test_file = Path(__file__).parent / "test_mcp_integration.py"

    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        sys.exit(1)

    success = validate_test_file(test_file)
    sys.exit(0 if success else 1)
