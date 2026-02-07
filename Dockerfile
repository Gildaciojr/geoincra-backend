FROM python:3.11-slim

# =========================
# Diretório da aplicação
# =========================
WORKDIR /app

# =========================
# Dependências de sistema
# (CRÍTICO para PDF / WeasyPrint)
# =========================
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

# =========================
# Dependências Python
# =========================
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# =========================
# Código da aplicação
# =========================
COPY . .

# =========================
# Variáveis de ambiente
# =========================
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# =========================
# Inicialização do backend
# =========================
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
