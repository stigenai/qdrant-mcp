## Repository Structure
- This directory is a worktree based git repo. The root is empty. Folders are branches, main to main, etc.

## Project Goals
- Goal: we want to develop a qrant single node server and mcp client all in one. This repo will create a docker container to run the latest qdrant server and wrap it in a rest based API to submit vectors and search vectors. In addition, this server will also act as an MCP server that can be connected via claude-code.

## Development Requirements
- We want to support the claude vector hooks found in ~/.claude/hooks/;
- Review the hooks files for vectors and make sure to provide support in this repos.

## Qdrant Resources
- Official Qdrant repositories:
  - Main Qdrant Server: https://github.com/qdrant/qdrant
  - Qdrant Client: https://github.com/qdrant/qdrant-client
  - MCP Server Qdrant Implementation: https://github.com/qdrant/mcp-server-qdrant

## Development Workflow
- Using THINK, test often, checkpoint and commit when everything is working.