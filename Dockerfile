# 1. Use an official, lightweight Python image
FROM python:3.11-slim

# 2. Set environment variables to keep Python from buffering logs or writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Set the working directory inside the container
WORKDIR /app

# 4. Copy your requirements file and install dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt
RUN python manage.py collectstatic --noinput
# 5. Copy the rest of your project code into the container
COPY . /app/

# 6. Expose the port Django runs on
EXPOSE 8000

# 7. Start the production server using Gunicorn
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]