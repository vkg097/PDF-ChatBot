# Enable BuildKit optimization
FROM python:3.10-slim

WORKDIR /app

# Prevent Python from writing bytecode and buffer issues
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install minimal OS dependencies and clean cache immediately
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install dependencies without caching downloaded wheels locally
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "main1.py", "--server.port=8501", "--server.address=0.0.0.0"]