# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the MCP server code
COPY google_places_mcp.py .
COPY app.py .

# Expose port for HTTP server
EXPOSE 8080

# Set environment variable for port
ENV PORT=8080

# Run using uvicorn to serve FastMCP as an ASGI app
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
