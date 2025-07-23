# GitHub Actions Workflows

This directory contains CI/CD workflows for the Qdrant MCP project.

## Workflows

### 1. Build and Push Docker Image (`docker-build-push.yml`)
- **Triggers**: Push to main/develop, tags, PRs, manual
- **Purpose**: Build multi-arch Docker images and push to GitHub Container Registry
- **Features**:
  - Multi-platform builds (amd64, arm64)
  - Security scanning with Trivy
  - Container structure tests
  - SBOM generation
  - Automatic releases for tags

### 2. Development Build (`dev-build.yml`)
- **Triggers**: Push to feature branches, PRs
- **Purpose**: Build and test development images
- **Features**:
  - Uses Dockerfile.dev for faster builds
  - Tests container startup
  - Comments on PRs with build status

### 3. Security Scan (`security-scan.yml`)
- **Triggers**: Push to main/develop, PRs, daily schedule
- **Purpose**: Continuous security monitoring
- **Features**:
  - Trivy vulnerability scanning
  - CodeQL analysis
  - Python dependency auditing
  - Security reports upload

### 4. Update Dependencies (`dependency-update.yml`)
- **Triggers**: Weekly schedule, manual
- **Purpose**: Automated dependency updates
- **Features**:
  - Updates all Python dependencies
  - Runs tests with new dependencies
  - Creates PR with changes

### 5. Dependabot (`dependabot.yml`)
- **Purpose**: Automated dependency version updates
- **Features**:
  - Grouped updates for dev/prod dependencies
  - Weekly schedule
  - Covers Python, Docker, and GitHub Actions

## Secrets Required

The following secrets need to be configured in the repository:

1. **GITHUB_TOKEN**: Automatically provided by GitHub Actions
2. **CODECOV_TOKEN**: (Optional) For coverage reporting

## Container Registry

Images are pushed to GitHub Container Registry (ghcr.io):
- Production: `ghcr.io/stigenai/qdrant-mcp:latest`
- Tagged: `ghcr.io/stigenai/qdrant-mcp:v1.0.0`
- Development: `ghcr.io/stigenai/qdrant-mcp:dev-<sha>`
- PR: `ghcr.io/stigenai/qdrant-mcp:pr-<number>`

## Manual Triggers

Most workflows support manual triggering via `workflow_dispatch`.
For the main build workflow, you can optionally push images even from PRs.

## Security

- All workflows use minimal required permissions
- Security scanning results are uploaded to GitHub Security tab
- Vulnerabilities are reported via GitHub Security Advisories
- Container images are scanned before pushing