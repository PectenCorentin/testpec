
########## UPDATE ##########
#Date updated : 26/11/2019 / Name : Baptiste PITEL  / Description : PEC-1201 add error logger

from google.cloud.exceptions import GoogleCloudError, NotFound
import os
from sqlalchemy import *
import json
from google.cloud import datastore
from google.cloud import bigquery
from google.cloud import storage
import time
import sys
import copy
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

import argparse
from pecten_utils.Storage import Storage
from pecten_utils import BigQueryLogsHandler 
import logging, logging.handlers

class Storage:
    def __init__(self, google_key_path=None):
        if google_key_path:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = google_key_path
            self.bigquery_client = bigquery.Client()
        else:
            self.bigquery_client = None
	
	
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        handler = BigQueryLogsHandler(self,args)
        handler.setLevel(logging.INFO)
        logger.addHandler(handler)

        self.args = args
        self.args.logger = logger



    def read_spreadsheet(self, spreadsheet_name):
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_name(os.environ['GOOGLE_APPLICATION_CREDENTIALS'], scope)
        gc = gspread.authorize(credentials)
        wks = gc.open(spreadsheet_name).sheet1
        df = pd.DataFrame(wks.get_all_records())
        return df

    def upload_to_cloud_storage(self, google_key_path, bucket_name, source, destination):
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = google_key_path

        try:
            client = storage.Client()
            bucket = client.get_bucket(bucket_name)
            blob = bucket.blob(destination)
            blob.upload_from_filename(source)

            return True
        except GoogleCloudError as e:
            print(str(e))
            return None
        except NotFound as e:
            print(str(e))
            return None

    def save_to_local_file(self, data, destination, mode="w"):
        if isinstance(data, str):
            with open(destination, mode) as f:
                f.write(data)
        elif isinstance(data, dict):
            with open(destination, mode) as f:
                f.write(json.dumps(data) + '\n')
        elif isinstance(data,list):
            if data and isinstance(data[0], dict):
                with open(destination, mode) as f:
                    for item in data:
                        #f.write(jsonpickle.encode(item, unpicklable=False) + '\n')
                        f.write(json.dumps(item) + '\n')
						

    def get_sql_data(self, sql_connection_string=None, sql_table_name=None,
                     sql_column_list=None, sql_where=None):
        engine = create_engine(sql_connection_string)
        metadata = MetaData(engine)

        source_table = Table(sql_table_name, metadata, autoload=True)
        projection_columns = [source_table.columns[name] for name in sql_column_list]

        if sql_where:
            statement = select(projection_columns).where(sql_where(source_table.columns))
        else:
            statement = select(projection_columns)
        result = statement.execute()
        rows = result.fetchall()
        result.close()
        return rows

    def get_sql_data_text_query(self, sql_connection_string, query):
        s = text(query)
        engine = create_engine(sql_connection_string)
        conn = engine.connect()
        rows = conn.execute(s)

        return rows

    def insert_to_sql(self, sql_connection_string=None, sql_table_name=None, data=None):
        engine = create_engine(sql_connection_string)
        metadata = MetaData(engine)

        source_table = Table(sql_table_name, metadata, autoload=True)
        statement = source_table.insert().values(data)
        result = statement.execute()

    def insert_to_datastore(self, project_id,google_key_path, data, kind, key_name):
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = google_key_path
        client = datastore.Client(project_id)

        if isinstance(data, list):
            for item in data:
                with client.batch() as batch:
                    # batch isnert
                    # The name/ID for the new entity
                    name = item[key_name]
                    item.pop(key_name)
                    # The Cloud Datastore key for the new entity
                    key = client.key(kind, name)

                    # Prepares the new entity
                    entity = datastore.Entity(key=key)
                    entity.update(item)
                    batch.put(entity)

    def get_bigquery_data(self, query, timeout=None, iterator_flag=True, params=[]):
        #params is a list of tuples of type (name of parameter,type,value)
        if self.bigquery_client:
            client = self.bigquery_client
        else:
            client = bigquery.Client()

        print("Running query...")
        if params:
            query_parameters = [bigquery.ScalarQueryParameter(*item) for item in params]

            job_config = bigquery.QueryJobConfig()
            job_config.query_parameters = query_parameters
            query_job = client.query(query,job_config=job_config)
        else:
            query_job = client.query(query)

        iterator = query_job.result(timeout=timeout)

        if iterator_flag:
            return iterator
        else:
            return list(iterator)

    def get_bigquery_data_legacy(self, query, timeout=None, iterator_flag=True):
        if self.bigquery_client:
            client = self.bigquery_client
        else:
            client = bigquery.Client()

        config = bigquery.job.QueryJobConfig()
        config.use_legacy_sql = True

        print("Running query...")
        query_job = client.query(query, job_config=config)
        iterator = query_job.result(timeout=timeout)

        if iterator_flag:
            return iterator
        else:
            return list(iterator)

    def insert_bigquery_data(self, dataset_name, table_name, data):
        if self.bigquery_client:
            client = self.bigquery_client
        else:
            self.bigquery_client = bigquery.Client()
            client = self.bigquery_client

        try:
            dataset_ref = client.dataset(dataset_name)
            dataset = bigquery.Dataset(dataset_ref)
            table_ref = dataset.table(table_name)
            table = client.get_table(table_ref)
        except Exception as e:
            print(e)
            self.args.logger.error(str(e),extra={"dataset":self.args.environment, "table_name" : table_name,
                                                "operation":"find table, Storage","script_type":"utils"})
            return None
	
        field_names={}
        for field in table.schema:
            if(field.field_type == "RECORD"):
                temp={}
                for item in field.fields:
                    if (item.mode == "REPEATED"):
                        temp[item.name] = []   #store empty list if mode is REPEATED
                    else:
                        temp[item.name] = None	
                field_names[field.name]=temp
            else:
                if(field.mode =="REPEATED"):
                    field_names[field.name] = []
                else:
                    field_names[field.name] = None   
		
        temp_data = []
        for item in data:
            temp=copy.deepcopy(field_names)
            for element in item.keys():    
                temp[element]=item[element]
            temp_data.append(temp)

        to_insert = []
        for row in temp_data:
            to_insert.append(row)

            if len(to_insert) == 10000 or sys.getsizeof(to_insert) > 9000000:
                try:
                    errors = client.insert_rows(table, to_insert)  # API request
                    to_insert = []
                    if errors:
                        print(errors)
                        return None
                except Exception as e:
                    print(e)
                    self.args.logger.error(str(e),extra={"dataset":self.args.environment, "table_name" : table,
                                                    "operation":"insert_rows, Storage","script_type":"utils"})
                    return None

        if len(to_insert) > 0:
            try:
                errors = client.insert_rows(table, to_insert)  # API request
                to_insert = []
                if errors:
                    print(errors)
                    return None
            except Exception as e:
                print(e)
                self.args.logger.error(str(e),extra={"dataset":self.args.environment, "table_name" : table,
                                                    "operation":"insert_rows, Storage","script_type":"utils"})
                return None

        return True

    @classmethod
    def convert_timestamp(cls, date_object):
        ts = time.strftime('%Y-%m-%d %H:%M:%S', date_object.timetuple())
        return ts

if __name__ == "__main__":
    pass