FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Startup script: migrations + init admin + runserver
RUN printf '#!/bin/bash\nset -e\npython manage.py migrate\npython manage.py init_admin\npython manage.py collectstatic --noinput\nexec python manage.py runserver 0.0.0.0:8000\n' > /app/startup.sh && chmod +x /app/startup.sh

CMD ["/bin/bash", "/app/startup.sh"]
