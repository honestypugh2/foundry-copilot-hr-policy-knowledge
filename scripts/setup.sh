#!/usr/bin/env bash
# Setup script for HR Policy Knowledge Agent
set -euo pipefail

echo "=========================================="
echo " HR Policy Knowledge Agent - Setup"
echo "=========================================="

# Check Python version
python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
echo "Python version: $python_version"

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -e ".[dev]"

# Check for .env file
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠ No .env file found. Copying from .env.example..."
    cp .env.example .env
    echo "  Please edit .env with your Azure service credentials."
fi

# Frontend setup
echo ""
echo "Setting up frontend..."
cd src/frontend
if command -v npm &> /dev/null; then
    npm install
    echo "Frontend dependencies installed."
else
    echo "⚠ npm not found. Install Node.js to set up the frontend."
fi
cd ../..

echo ""
echo "=========================================="
echo " Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Edit .env with your Azure credentials"
echo "  2. Index the knowledge base:"
echo "     python -m scripts.index_knowledge_base"
echo "  3. Start the backend:"
echo "     python -m src.backend.main"
echo "  4. Start the frontend (in another terminal):"
echo "     cd src/frontend && npm run dev"
echo ""
