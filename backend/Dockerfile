FROM python:3.12-slim

WORKDIR /app

# Copy global requirements
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy project folders
COPY backend /app/backend
COPY simulator /app/simulator
COPY data /app/data

WORKDIR /app/backend

EXPOSE 5000

CMD ["python", "app.py"]
