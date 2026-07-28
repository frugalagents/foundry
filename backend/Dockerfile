FROM public.ecr.aws/lambda/python:3.12

WORKDIR /var/task

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend .
COPY PlatformAdvisorAgent/app/PlatformAdvisorAgent /opt/platform-advisor

ENV PYTHONPATH=/var/task:/opt/platform-advisor
ENV DEV_MODE=false

CMD ["api.main.handler"]
