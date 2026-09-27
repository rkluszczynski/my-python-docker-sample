FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

EXPOSE 9000

CMD ["python", "-m", "uvicorn", "src.execute_server:app", "--host", "0.0.0.0", "--port", "9000"]
