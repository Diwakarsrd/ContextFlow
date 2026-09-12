import os
import subprocess

files = [
    r'src\contextflow\mcp\http_transport.py',
    r'src\contextflow\mcp\server.py',
    r'tests\test_mcp_auth.py'
]

for f in files:
    with open(f, 'r') as file:
        content = file.read()
    content = content.replace('mcp.server.lowlevel', 'mcp.server.mcpserver')
    content = content.replace('Server', 'MCPServer')
    content = content.replace('MCPMCPServer', 'MCPServer') 
    content = content.replace('MCPServer.MCPServer', 'MCPServer')
    with open(f, 'w') as file:
        file.write(content)

toml_file = 'pyproject.toml'
with open(toml_file, 'r') as file:
    content = file.read()
content = content.replace('\"mcp>=1.0\"', '\"mcp==1.0.0\"')
with open(toml_file, 'w') as file:
    file.write(content)

subprocess.run(['git', 'add', '-A'], check=True)
subprocess.run(['git', 'commit', '-m', 'fix: pin mcp version to 1.0.0 to fix CI tests'], check=True)
subprocess.run(['git', 'push', 'origin', 'main'], check=True)
