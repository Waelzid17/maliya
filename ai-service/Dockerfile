FROM python:3.12-slim
WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
# PyTorch CPU : ~200 Mo au lieu de plusieurs Go pour la version CUDA
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app ./app
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=60s CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/sante')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
