# syntax=docker/dockerfile:1
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt ./

# Use the cache mount here too
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

COPY . .

# Refined startup script
RUN printf '#!/bin/bash\nset -e\npython manage.py migrate\npython manage.py init_admin\nexec python manage.py runserver 0.0.0.0:8000\n' > /app/startup.sh && chmod +x /app/startup.sh

CMD ["/bin/bash", "/app/startup.sh"]