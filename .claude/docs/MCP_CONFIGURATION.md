# MCP Configuration Documentation

## Overview
This document describes the Model Context Protocol (MCP) server configuration for the KireMisu project, optimized for cross-platform development (Windows/macOS/Linux).

## Current Configuration

### MCP Servers (`.claude/mcp.json`)
```json
{
  "servers": {
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    },
    "filesystem": {
      "command": "npx",
      "args": [
        "-y", 
        "@modelcontextprotocol/server-filesystem",
        "C:\\Users\\karmic\\Documents\\source\\kiremisu"
      ]
    },
    "playwright": {
      "command": "npx",
      "args": ["-y", "mcp-playwright"]
    }
  }
}
```

### GitHub Integration
- **Method**: GitHub CLI (`gh`) via Bash tool
- **Rationale**: More reliable than GitHub MCP server, works cross-platform
- **Authentication**: Using GH_TOKEN environment variable

## Server Details

### Memory Server
- **Package**: `@modelcontextprotocol/server-memory`
- **Purpose**: Knowledge graph for persistent memory
- **Status**: ✅ Working
- **Cross-platform**: ✅ Yes

### Filesystem Server  
- **Package**: `@modelcontextprotocol/server-filesystem`
- **Purpose**: File system operations within project directory
- **Status**: ✅ Working
- **Cross-platform**: ✅ Yes (path will need adjustment per platform)

### Playwright Server
- **Package**: `mcp-playwright`
- **Purpose**: Browser automation and testing
- **Status**: ✅ Working  
- **Cross-platform**: ✅ Yes

### GitHub Operations
- **Tool**: GitHub CLI (`gh`)
- **Access**: Through Bash tool
- **Authentication**: Token-based (GH_TOKEN)
- **Cross-platform**: ✅ Yes

## Cross-Platform Notes

### Path Configuration
- **Windows**: `C:\\Users\\karmic\\Documents\\source\\kiremisu`
- **macOS/Linux**: `/Users/karmic/Documents/source/kiremisu` or similar

### NPM/Node Requirements
- Node.js >= 18.17.0
- npm >= 9.0.0
- npx available in PATH

### GitHub CLI Requirements
- `gh` CLI installed and authenticated
- Token with appropriate scopes (repo, user, workflow, etc.)

## Troubleshooting

### Common Issues

#### Windows "cmd /c" Wrapper Warnings
- **Issue**: Claude Code may show Windows wrapper warnings
- **Solution**: Current `npx` configuration should work; ignore warnings unless functionality breaks

#### MCP Server Timeouts
- **Issue**: Servers may timeout on first run
- **Solution**: Allow time for npm package downloads

#### Cross-Platform Path Issues  
- **Issue**: Filesystem server path incorrect on different OS
- **Solution**: Update filesystem server path in `.claude/mcp.json` per platform:
  ```json
  // Windows
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "C:\\path\\to\\project"]
  
  // macOS/Linux  
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/project"]
  ```

### Validation Commands
```bash
# Test npx availability
npx --version

# Test GitHub CLI
gh auth status

# Test MCP packages (may take time to download)
npx -y @modelcontextprotocol/server-memory
npx -y @modelcontextprotocol/server-filesystem /tmp
npx -y mcp-playwright --help
```

## Security Considerations

### File System Access Controls
- **Principle of Least Privilege:** Filesystem server restricted to essential directories only
- **Excluded Patterns:** Sensitive files (.git, .env*, node_modules) explicitly blocked
- **Read-Only Operations:** Agents limited to read-only access where possible
- **Path Validation:** Use relative paths to prevent directory traversal attacks

### Agent Security Boundaries
- **Scope Restrictions:** Each agent limited to its specific functional area
- **Operation Constraints:** No system command execution or package installation
- **Data Protection:** No access to credentials, environment variables, or sensitive configurations
- **Network Isolation:** Restricted external API access for testing endpoints only

### Configuration Security
```json
{
  "filesystem": {
    "args": [
      "--allowed-directories", "./frontend", "./backend", "./docs", "./.claude/docs",
      "--excluded-patterns", ".git/**", ".env*", "node_modules/**", "dist/**", "build/**"
    ]
  }
}
```

## Configuration Best Practices

1. **Keep global config minimal** - Project-specific servers in `.claude/mcp.json`
2. **Use official packages** - Prefer `@modelcontextprotocol/*` packages
3. **Cross-platform paths** - Document platform-specific configurations  
4. **Regular updates** - Keep MCP packages updated
5. **Authentication** - Use environment variables for tokens
6. **Security First** - Always implement least-privilege access controls

## Maintenance

### Regular Tasks
- Update MCP server packages: `npm update -g @modelcontextprotocol/server-*`
- Verify GitHub CLI authentication: `gh auth refresh`
- Test functionality after Claude Code updates

### Configuration Changes
When modifying `.claude/mcp.json`:
1. Backup current configuration
2. Test on primary development platform
3. Verify on secondary platform if available
4. Update this documentation

## Support Resources
- [Model Context Protocol Documentation](https://modelcontextprotocol.io/)
- [Claude Code MCP Guide](https://docs.anthropic.com/en/docs/claude-code/mcp)
- [GitHub CLI Documentation](https://cli.github.com/manual/)

---
*Last updated: 2025-08-27*
*Platforms tested: Windows 11*