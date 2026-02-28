#!/usr/bin/env bash
# =============================================================================
# setup.sh  -  Linux/macOS setup script for Email Agent
#
# Creates config.yaml and tasks/mappings.yaml from templates.
# These files contain sensitive data and are ignored by git.
# =============================================================================

set -e

echo ""
echo "============================================"
echo "  Email Agent Setup (Linux/macOS)"
echo "============================================"
echo ""

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Navigate to project root (two levels up from .github/scripts/)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "Project root: $PROJECT_ROOT"
echo ""

# -----------------------------------------------------------------------------
# Create config.yaml
# -----------------------------------------------------------------------------
# Define template directory
TEMPLATE_DIR="$PROJECT_ROOT/.github/scripts/template"

if [[ -f "$PROJECT_ROOT/config.yaml" ]]; then
    echo "[SKIP] config.yaml already exists"
else
    if [[ -f "$TEMPLATE_DIR/config.template.yaml" ]]; then
        cp "$TEMPLATE_DIR/config.template.yaml" "$PROJECT_ROOT/config.yaml"
        echo "[DONE] Created config.yaml from template"
        echo "       > Edit config.yaml with your email credentials"
    else
        echo "[ERROR] Template config.template.yaml not found!"
    fi
fi

# -----------------------------------------------------------------------------
# Create tasks/mappings.yaml
# -----------------------------------------------------------------------------
if [[ ! -d "$PROJECT_ROOT/tasks" ]]; then
    mkdir -p "$PROJECT_ROOT/tasks"
    echo "[DONE] Created tasks/ directory"
fi

if [[ -f "$PROJECT_ROOT/tasks/mappings.yaml" ]]; then
    echo "[SKIP] tasks/mappings.yaml already exists"
else
    if [[ -f "$TEMPLATE_DIR/mappings.template.yaml" ]]; then
        cp "$TEMPLATE_DIR/mappings.template.yaml" "$PROJECT_ROOT/tasks/mappings.yaml"
        echo "[DONE] Created tasks/mappings.yaml from template"
        echo "       > Edit tasks/mappings.yaml with your task configurations"
    else
        echo "[ERROR] Template mappings.template.yaml not found!"
    fi
fi

# -----------------------------------------------------------------------------
# Create empty sent_log.json if it doesn't exist
# -----------------------------------------------------------------------------
if [[ -f "$PROJECT_ROOT/sent_log.json" ]]; then
    echo "[SKIP] sent_log.json already exists"
else
    echo "{}" > "$PROJECT_ROOT/sent_log.json"
    echo "[DONE] Created empty sent_log.json"
fi

echo ""
echo "============================================"
echo "  Setup Complete!"
echo "============================================"
echo ""
echo "IMPORTANT: Before running the agent:"
echo "  1. Edit config.yaml with your CPanel email credentials"
echo "  2. Edit tasks/mappings.yaml with your task mappings"
echo ""
echo "WARNING: These files contain sensitive data!"
echo "         They are already in .gitignore and will NOT be committed."
echo ""
echo "To start the agent: python3 agent.py"
echo ""
