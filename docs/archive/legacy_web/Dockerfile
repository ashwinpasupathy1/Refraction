FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy refraction package
COPY refraction/ ./refraction/

# Copy built React SPA (build with: cd plotter_web && npm run build)
COPY plotter_web/dist ./plotter_web/dist/

# Install Python dependencies (web-only, no Tk/matplotlib)
RUN pip install --no-cache-dir \
    fastapi uvicorn plotly pandas openpyxl scipy numpy

# Expose port
EXPOSE 7331

# Run FastAPI server (web-only mode, no Tk)
CMD ["python3", "-c", "from refraction.server.api import _make_app; import uvicorn; uvicorn.run(_make_app(), host='0.0.0.0', port=7331)"]
