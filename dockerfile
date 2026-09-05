FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed for PyPDF / FAISS
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/get/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose Streamlit's default port
EXPOSE 8501

# Streamlit config settings for container environment
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

CMD ["streamlit", "run", "nain1.py"]