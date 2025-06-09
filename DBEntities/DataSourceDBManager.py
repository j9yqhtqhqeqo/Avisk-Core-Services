import sys
from pathlib import Path
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

from DBEntities.DataSourceDBEntity import DataSourceDBEntity
import pyodbc
from Utilities.Lookups import Lookups, Processing_Type, DB_Connection



DEV_DB_CONNECTION_STRING = DB_Connection().DEV_DB_CONNECTION_STRING
TEST_DB_CONNECTION_STRING = 'DRIVER={ODBC Driver 18 for SQL Server};SERVER=earthdevdb.database.windows.net;UID=earthdevdbadmin@earthdevdb.database.windows.net;PWD=3q45yE3fEgQej8h!@;database=earth-test'


class DataSourceDBManager():

    def __init__(self, database_context: None) -> None:

        connection_string = ''

        if (database_context == 'Development'):
            connection_string = DEV_DB_CONNECTION_STRING
        elif (database_context == 'Test'):
            connection_string = TEST_DB_CONNECTION_STRING
        else:
            raise Exception("Database context Undefined")

        self.dbConnection = pyodbc.connect(connection_string)
        self.get_batch_id = self.get_batch_id()

    def get_batch_id(self):

        cursor = self.dbConnection.cursor()
        cursor.execute("select max(batch_id) from dbo.t_document")
        last_batch_id = cursor.fetchone()[0]
        if last_batch_id is None:
            new_batch_id = 1
        else:
            new_batch_id = last_batch_id + 1

        return new_batch_id

    # Get unprocessed data source List

    def get_unprocessed_content_list(self):
        document_list = []
        try:
            cursor = self.dbConnection.cursor()
            cursor.execute(" select d.unique_id ,d.company_name ,d.year ,d.content_type,l.data_lookups_description, d.source_type , d.source_url ,d.processed_ind\
                            from t_data_source d INNER join  t_data_lookups l on d.content_type = l.data_lookups_id\
                            where d.processed_ind = 0 order by d.unique_id")
            rows = cursor.fetchall()
            for row in rows:

                file_name = row.company_name + ' ' + \
                    str(row.year)+' '+row.data_lookups_description + \
                    '.txt'
                document_entity = DataSourceDBEntity(
                    unique_id=row.unique_id,
                    company_name=row.company_name,
                    year=row.year,
                    content_type=row.content_type,
                    content_type_desc=row.data_lookups_description,
                    source_type=row.source_type,
                    source_url=row.source_url,
                    processed_ind=row.processed_ind,
                    document_name=file_name
                )
                document_list.append(document_entity)
            cursor.close()
        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

        return document_list

    def add_stage1_processed_files_to_t_document(self, data_source_db_entity: DataSourceDBEntity, flagged_for_review: bool):
        # Create a cursor object to execute SQL queries
        cursor = self.dbConnection.cursor()

        # Delete the t_document entry if it already exists
        sql = 'delete t_document where document_id = ?'
        cursor.execute(sql, data_source_db_entity.unique_id)
        self.dbConnection.commit()

        # Construct the INSERT INTO statement

        insert_sql = f"INSERT INTO dbo.t_document\
                (document_id , document_name, company_name,year,content_type,\
                    exp_pathway_keyword_search_completed_ind,internalization_keyword_search_completed_ind,\
                    mitigation_search_completed_ind,exp_insights_generated_ind,int_insights_generated_ind,\
                    int_exp_insights_generated, mitigation_exp_insights_generated,mitigation_int_insights_generated,\
                    mitigation_int_exp_insights_generated,added_dt,added_by ,modify_dt,modify_by, batch_id\
                )\
                VALUES\
                ({data_source_db_entity.unique_id},N'{data_source_db_entity.document_name}',N'{data_source_db_entity.company_name}', {data_source_db_entity.year},{data_source_db_entity.content_type},\
                        0,0,0,0,0,0,0,0,0,CURRENT_TIMESTAMP, N'Mohan Hanumantha',CURRENT_TIMESTAMP, N'Mohan Hanumantha',{self.get_batch_id}\
                )"

        review_flag = 0
        if (flagged_for_review):
            review_flag = 1
        update_sql = f"update t_data_source set processed_ind = 1, flagged_for_review = {review_flag}, modify_dt = CURRENT_TIMESTAMP where unique_id = {data_source_db_entity.unique_id}"

        try:
            # Execute the SQL query
            cursor.execute(insert_sql)
            cursor.execute(update_sql)

        except Exception as exc:
            # Rollback the transaction if any error occurs
            self.dbConnection.rollback()
            print(f"Error: {str(exc)}")
            raise exc
        # Close the cursor and connection
        self.dbConnection.commit()
        cursor.close()

    def update_data_source_processed_indicator(self, document_list=None):
        pass

    def datafix_load_t_document_bulk(self):

        document_list = self.get_unprocessed_content_list()

        for document in document_list:
            self.add_stage1_processed_files_to_t_document(document, False)


data_src_mgr = DataSourceDBManager("Development")
data_src_mgr.datafix_load_t_document_bulk()
