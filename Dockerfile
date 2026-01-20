FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY energy_scheduler.py .
COPY energy_model.pkl .
CMD ["python", "energy_scheduler.py"]1~FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY energy_scheduler.py .
COPY energy_model.pkl .
CMD ["python", "energy_scheduler.py"]
