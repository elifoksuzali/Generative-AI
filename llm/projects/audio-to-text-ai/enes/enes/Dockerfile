# Base image with CUDA support
# FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04
# dosya dogru kurulumları

FROM nvidia/cuda:12.4.0-runtime-ubuntu22.04
# Set up the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Copy your Flask app and model
COPY . .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Expose the Flask app's port
EXPOSE 5000

# Command to run the app
CMD ["python3", "proje.py"]
