#!/bin/bash
set -e

echo "Building secure Qdrant MCP Docker image..."
echo "========================================="

# Build the image
echo "Step 1: Building Docker image..."
docker build -t qdrant-mcp:secure .

# Get image size
echo -e "\nStep 2: Image size analysis..."
docker images qdrant-mcp:secure --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}"

# Check if we're running as non-root
echo -e "\nStep 3: Verifying non-root user..."
docker run --rm qdrant-mcp:secure whoami

# List installed packages for audit
echo -e "\nStep 4: Installed packages audit..."
docker run --rm qdrant-mcp:secure dpkg -l | grep -E '^ii' | wc -l
echo "Total packages installed: $(docker run --rm qdrant-mcp:secure dpkg -l | grep -E '^ii' | wc -l)"

# Security scan with trivy if available
if command -v trivy &> /dev/null; then
    echo -e "\nStep 5: Running security scan with Trivy..."
    trivy image --severity HIGH,CRITICAL qdrant-mcp:secure
else
    echo -e "\nStep 5: Trivy not found. Install it for security scanning:"
    echo "  brew install aquasecurity/trivy/trivy  # macOS"
    echo "  sudo apt-get install trivy              # Ubuntu/Debian"
fi

# Test the image
echo -e "\nStep 6: Testing the image..."
echo "Starting container for testing..."
CONTAINER_ID=$(docker run -d --rm \
    --name qdrant-mcp-test \
    -p 8000:8000 -p 8001:8001 -p 6333:6333 \
    qdrant-mcp:secure)

echo "Waiting for services to start..."
sleep 30

# Test endpoints
echo "Testing endpoints..."
for endpoint in "http://localhost:6333/health" "http://localhost:8000/health"; do
    if curl -s -f "$endpoint" > /dev/null; then
        echo "✓ $endpoint is responding"
    else
        echo "✗ $endpoint is not responding"
    fi
done

# Check processes are running as non-root
echo -e "\nChecking process ownership..."
docker exec qdrant-mcp-test ps aux | grep -E "(qdrant|python)" | head -5

# Cleanup
echo -e "\nCleaning up test container..."
docker stop qdrant-mcp-test

echo -e "\nBuild complete! To run the secure container:"
echo "  docker run -d --name qdrant-mcp \\"
echo "    --security-opt no-new-privileges:true \\"
echo "    --read-only \\"
echo "    --tmpfs /tmp --tmpfs /var/run --tmpfs /var/log/supervisor \\"
echo "    -v qdrant-data:/qdrant/storage \\"
echo "    -p 127.0.0.1:8000:8000 \\"
echo "    -p 127.0.0.1:8001:8001 \\"
echo "    -p 127.0.0.1:6333:6333 \\"
echo "    qdrant-mcp:secure"