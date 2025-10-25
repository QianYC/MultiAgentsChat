"""
Helper script to get GitHub Copilot token from VS Code.
Run this to automatically extract and save your GitHub token.
"""
import os
import json
import subprocess
from pathlib import Path


def get_github_token_vscode():
    """Extract GitHub token from VS Code's secret storage."""
    try:
        # Try to get token using VS Code CLI
        result = subprocess.run(
            ["code", "--list-extensions"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if "github.copilot" not in result.stdout.lower():
            print("❌ GitHub Copilot extension not installed in VS Code")
            return None
        
        print("✅ GitHub Copilot extension found")
        print("\n📝 To get your token:")
        print("1. In VS Code, press Cmd+Shift+P (Mac) or Ctrl+Shift+P (Windows/Linux)")
        print("2. Type: 'GitHub Copilot: Get Token'")
        print("3. Copy the token")
        print("4. Paste it below")
        print()
        
        return None
        
    except Exception as e:
        print(f"⚠️  Could not auto-detect: {e}")
        return None


def save_token_to_env(token: str):
    """Save token to .env file."""
    env_file = Path(".env")
    
    # Read existing .env or create from template
    if env_file.exists():
        with open(env_file, 'r') as f:
            lines = f.readlines()
    else:
        # Copy from .env.example
        example_file = Path(".env.example")
        if example_file.exists():
            with open(example_file, 'r') as f:
                lines = f.readlines()
        else:
            lines = []
    
    # Update or add GITHUB_TOKEN
    found = False
    for i, line in enumerate(lines):
        if line.startswith("GITHUB_TOKEN="):
            lines[i] = f"GITHUB_TOKEN={token}\n"
            found = True
            break
    
    if not found:
        lines.insert(0, f"GITHUB_TOKEN={token}\n")
    
    # Write back
    with open(env_file, 'w') as f:
        f.writelines(lines)
    
    print(f"✅ Token saved to {env_file}")


def main():
    """Main function."""
    print("=" * 60)
    print("GitHub Copilot Token Setup")
    print("=" * 60)
    print()
    
    # Try to auto-detect
    token = get_github_token_vscode()
    
    # Manual input
    print("\n" + "=" * 60)
    print("Manual Token Entry")
    print("=" * 60)
    print()
    print("Get your GitHub token:")
    print("  • VS Code: Cmd/Ctrl+Shift+P → 'GitHub Copilot: Get Token'")
    print("  • GitHub: https://github.com/settings/tokens")
    print()
    
    token = input("Paste your GitHub token here (or press Enter to skip): ").strip()
    
    if token:
        save_token_to_env(token)
        print("\n✅ Setup complete! Run 'python main.py' to start")
    else:
        print("\n⚠️  No token provided. Please add GITHUB_TOKEN to .env manually")
        print("   Example: GITHUB_TOKEN=gho_xxxxxxxxxxxxx")


if __name__ == "__main__":
    main()
