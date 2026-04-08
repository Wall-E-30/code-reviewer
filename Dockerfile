# Use a lightweight Python base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Environment variables for OpenEnv (defaults)
ENV API_BASE_URL="https://router.huggingface.co/v1"
ENV MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"

# The command to run your inference
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]