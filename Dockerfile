# Use Python 3.12 slim image
FROM python:3.11

# Set the working directory within the container
WORKDIR /app

RUN apt -qq update
RUN apt -qq install -y --no-install-recommends \
    curl \
    git 

# sets the TimeZone, to be used inside the container
ENV TZ Asia/Kolkata

# Copy requirements.txt and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the rest of your project code
COPY . .

# Command to run when the container starts
CMD ["python3", "-m", "clonebot"]
