FROM python:3.11.6-bookworm
RUN apt-get update && apt-get install -y git awscli default-jre graphviz && apt-get clean
ENV AWS_DEFAULT_REGION eu-west-1
RUN git clone -n --depth=1 --filter=tree:0 https://github.com/Opetushallitus/koski && cd koski && git sparse-checkout set --no-cone documentation/tietokantaskeemat && git checkout && ls -la
COPY document_generator.py databases.json index.html.template *.jar requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "document_generator.py"]