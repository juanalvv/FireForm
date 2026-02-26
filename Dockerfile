
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl build-essential libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN python -m pip install --upgrade pip 
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set Python path so imports work correctly
ENV PYTHONPATH=/app/src

# Keep container running for interactive use
CMD ["tail", "-f", "/dev/null"]
