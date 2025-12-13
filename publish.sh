#!/bin/bash
# Publish Socket_Singleton to PyPI
# Usage: ./publish.sh

set -e

echo "Installing build dependencies..."
pip install --upgrade build twine

echo "Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info

echo "Building package..."
python -m build

echo "Checking package..."
twine check dist/*

echo ""
echo "Build complete! Files created in dist/:"
ls -lh dist/

echo ""
echo "To upload to PyPI, run:"
echo "  twine upload dist/*"
echo ""
echo "To upload to TestPyPI first (recommended), run:"
echo "  twine upload --repository testpypi dist/*"

