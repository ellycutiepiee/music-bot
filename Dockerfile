# Use a lightweight Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (FFmpeg is required for music, git for some pip packages)
RUN apt-get update && \
    apt-get install -y ffmpeg git build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the bot code
COPY . .

# Run the bot
CMD ["python", "bot.py"]
