# --- STAGE 1: Build React Frontend ---
FROM node:22-slim AS build-stage
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# --- STAGE 2: Final Image ---
FROM python:3.11-slim
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Copy the built frontend from Stage 1
COPY --from=build-stage /app/frontend/dist /app/frontend/dist

# Environment variables for OpenEnv
ENV API_BASE_URL="https://router.huggingface.co/v1"
ENV MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
ENV PORT=7860

# Entry point starts the FastAPI engine
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]