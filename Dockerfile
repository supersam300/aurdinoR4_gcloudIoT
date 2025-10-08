
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Run the web server using gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "main:app"]
