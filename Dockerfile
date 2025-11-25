FROM python:3.9-slim

WORKDIR /app

# Install system dependencies in one layer
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY energy_scheduler_extender.py .
COPY corrected_energy_model.pkl .

EXPOSE 8080

CMD ["python", "energy_scheduler_extender.py"]
