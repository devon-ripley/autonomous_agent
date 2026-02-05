FROM python:3.11-slim

# Install system dependencies
ENV PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y \
    git \
    curl \
    sudo \
    build-essential \
    vim \
    nano \
    iputils-ping \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# Create generic user
RUN useradd -m -s /bin/bash autoagent && \
    usermod -aG sudo autoagent

# Configure sudo to allow passwordless execution IF defaults needed,
# But we are using the executor to inject password. 
# However, to be safe for manual interaction:
# RUN echo "autoagent ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
# Actually, the user wants auth simulation, so we set a password.
RUN echo "autoagent:sudo" | chpasswd

# Set working directory
WORKDIR /app

# Copy requirements first to leverage cache
COPY requirements.txt .

# Optimize: Install CPU-only PyTorch to save ~2GB
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Fix permissions
RUN chown -R autoagent:autoagent /app

# Switch to user
USER autoagent

# Default command
CMD ["python", "autonomous_agent.py"]
