# Imagen de diagnóstico sin Python SDK de Azure CLI y sin servidor HTTP.
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /opt/g7b
RUN pip install --no-cache-dir "azure-identity>=1.19,<2" "azure-storage-blob>=12.20,<13" \
    && useradd --create-home --uid 10001 g7b
COPY g7b_ops/ /opt/g7b/g7b_ops/
USER 10001
CMD ["python", "-m", "g7b_ops.auditoria"]
