#!/usr/bin/env python
import airspeed
import boto3
import json
import os
import subprocess
import shutil
from airspeed import CachingFileLoader
from time import gmtime, strftime


db_docs_path = '/tmp/db_docs'
environment = os.getenv('ENVIRONMENT_NAME')
postgres_jar_file = './postgresql-42.6.0.jar'
schemaspy_jar_file = './schemaspy-6.2.4.jar'
ssm_client = boto3.client('ssm')
rds_client = boto3.client('rds')
database_dict = {}
version_dict = {}

description = """
DB Documentation generator

Generates DB documentation and syncs it to an S3 bucket
"""


def get_db_dict(environment_name):
    db_instances_list = rds_client.describe_db_instances(Filters=[{'Name': 'engine', 'Values': ['postgres']}])
    db_clusters_list = rds_client.describe_db_clusters(Filters=[{'Name': 'engine', 'Values': ['aurora-postgresql']}])
    for i in db_instances_list['DBInstances']:
        db_name = i['DBName']
        db_instance_identifier = i['DBInstanceIdentifier']
        endpoint = i['Endpoint']['Address']
        version = i['EngineVersion']
        if environment_name in db_instance_identifier:
            database_dict[db_name] = endpoint
            version_dict[db_name] = float(version)
    for i in db_clusters_list['DBClusters']:
        db_full_name = i['DBClusterIdentifier'].split('-')[0] + "-" + i['DBClusterIdentifier'].split('-')[1]
        db_name = db_full_name.split('-')[1]
        endpoint = i['ReaderEndpoint']
        version = i['EngineVersion']
        if environment_name in db_full_name:
            database_dict[db_name] = endpoint
            version_dict[db_name] = float(version)

def get_db_schemas(db_name):
    db_schema_conf = open('databases.json', 'r').read()
    db_schema_json = json.loads(db_schema_conf)
    if db_name in db_schema_json.get('databases'):
        db_schema_list = db_schema_json.get('databases').get(db_name).get('schemas')
        db_schemas = ','.join(db_schema_list)
    else:
        db_schemas = 'public'
    return db_schemas

def get_db_password(environment_name, db_name):
    ssm_parameter_name = f'/{environment_name}/postgresqls/{db_name}/app-user-password'
    database_password = ssm_client.get_parameter(Name=ssm_parameter_name, WithDecryption=True).get('Parameter').get('Value')
    return database_password


def generate_docs(db_host, db_name, db_schemas, db_version, db_password, db_docs_path, schemaspy_jar_path, postgres_jar_path):
    db_type = "pgsql" if db_version < 11.0 else "pgsql11"
    try:
        subprocess.run(["java", "-jar", schemaspy_jar_path, "-lq", "-t", db_type, "-dp", postgres_jar_path, "-host", db_host, "-port",
                                 "5432", "-db", db_name, "-u", "app", "-p", db_password, "-norows", "-schemas", db_schemas, "-o", f"{db_docs_path}/{db_name}"]
                                 , check=True, stdout=subprocess.PIPE).stdout
    except subprocess.CalledProcessError:
        print(f'Error generating docs for {db_name}')


def sync_docs(path, bucket):
    subprocess.run(['aws', 's3', 'sync', path, f's3://{bucket}'], check=True, stdout=subprocess.PIPE).stdout


def main():
    schemaspy_jar_path = schemaspy_jar_file
    postgres_jar_path = postgres_jar_file
    documentation_bucket = os.getenv('BUCKET')
    db_docs_path = '/tmp/db_docs'
    get_db_dict(environment)
    location = os.getcwd()

    generated_docs_list = []
    for db_name in database_dict:
        try:
            print(f'Starting on {environment}-{db_name}')
            db_host = database_dict[db_name]
            db_version = version_dict[db_name]
            db_password = get_db_password(environment, db_name)
            db_schemas = get_db_schemas(db_name)
            generate_docs(db_host, db_name, db_schemas, db_version, db_password, db_docs_path, schemaspy_jar_path, postgres_jar_path)
            print(f'Generated docs for {environment}-{db_name}')
            generation_time = strftime("%Y-%m-%d %H:%M:%S", gmtime())
            generated_docs_list.append({'name': db_name, 'generation_time': generation_time})
        except rds_client.exceptions.DBInstanceNotFoundFault:
            print(f'Error: {environment}-{db_name} database not found!')
    generation_time = strftime("%Y-%m-%d %H:%M:%S", gmtime())
    koski_folders = os.listdir('koski/documentation/tietokantaskeemat')
    for i in koski_folders:
        generated_docs_list.append({'name': i, 'generation_time': generation_time})
        shutil.copytree('koski/documentation/tietokantaskeemat/'+ i, '/tmp/db_docs/' + i, dirs_exist_ok=True)
    loader = CachingFileLoader(location)
    template = loader.load_template('index.html.template')
    output = template.merge(locals())
    f = open(db_docs_path + '/index.html', 'wt', encoding='utf-8')
    f.write(output)
    f.close()
    sync_docs(db_docs_path, documentation_bucket)

if __name__ == "__main__":
    main()