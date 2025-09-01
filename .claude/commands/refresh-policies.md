# Refresh Policy Understanding

Reloads and applies the latest organizational policies from the policy registry.

## Usage
`/refresh-policies`

## Actions Performed
1. Ensure EgoKit is installed with dependencies
2. Reload policy charter from registry
3. Merge hierarchical scope configurations
4. Update agent behavior calibration settings
5. Refresh detector configurations
6. Apply new validation rules

## Implementation
```bash
# Check if we're in a virtual environment with EgoKit
if ! command -v ego &> /dev/null; then
    echo "📦 Setting up EgoKit environment..."
    
    # Try to find and activate existing venv first
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    elif [ -f "../venv/bin/activate" ]; then
        source ../venv/bin/activate
    elif [ -f "../../venv/bin/activate" ]; then
        source ../../venv/bin/activate
    fi
    
    # If ego still not found, install dependencies
    if ! command -v ego &> /dev/null; then
        echo "📦 Installing missing dependencies..."
        pip install pydantic jsonschema pathspec pyyaml rich "typer[all]" --quiet
        
        # Try to install EgoKit if available locally
        if [ -d "./egokit" ]; then
            pip install -e "./egokit" --quiet
        elif [ -d "../egokit" ]; then
            pip install -e "../egokit" --quiet
        elif [ -d "$HOME/Work/EgoKit" ]; then
            pip install -e "$HOME/Work/EgoKit" --quiet
        fi
    fi
fi

# Verify ego is now available
if ! command -v ego &> /dev/null; then
    echo "❌ Unable to find or install EgoKit. Please ensure EgoKit is installed."
    echo "   Run: pip install -e /path/to/egokit"
    exit 1
fi

# Regenerate Claude Code artifacts
# Since this is a Claude-specific command, we always generate Claude artifacts
ego apply --repo . --agent claude

# Show current configuration
echo ""
echo "🔄 Policy configuration refreshed from registry"
echo "📋 Active configuration:"
ego doctor

echo ""
echo "✨ Updated behavior calibration applied for Claude Code"
```

## Integration Notes
Use this command after policy registry updates or when switching between projects with different requirements. The command will automatically handle dependency installation if needed.