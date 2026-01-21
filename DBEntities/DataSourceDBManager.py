from Utilities.Lookups import Lookups, Processing_Type, DB_Connection
import psycopg2.extras
import psycopg2
from DBEntities.DataSourceDBEntity import DataSourceDBEntity
import sys
from pathlib import Path
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))


DEV_DB_CONNECTION_STRING = DB_Connection().DEV_DB_CONNECTION_STRING
# TEST_DB_CONNECTION_STRING = 'Updated for GCC PostgreSQL when test environment is available'


class DataSourceDBManager():

    def __init__(self, database_context: None) -> None:

        connection_string = ''

        if (database_context == 'Development'):
            connection_string = DEV_DB_CONNECTION_STRING
        elif (database_context == 'Test'):
            raise Exception("Test database context not yet configured for GCC")
        else:
            raise Exception("Database context Undefined")

        self.dbConnection = psycopg2.connect(connection_string)
        self.get_batch_id = self.get_batch_id()

    def get_batch_id(self):

        cursor = self.dbConnection.cursor()
        cursor.execute("select max(batch_id) from t_document")
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

                file_name = row[1] + ' ' + \
                    str(row[2])+' '+row[4] + \
                    '.txt'
                document_entity = DataSourceDBEntity(
                    unique_id=row[0],
                    company_name=row[1],
                    year=row[2],
                    content_type=row[3],
                    content_type_desc=row[4],
                    source_type=row[5],
                    source_url=row[6],
                    processed_ind=row[7],
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
        sql = 'DELETE FROM t_document WHERE document_id = %s'
        cursor.execute(sql, (data_source_db_entity.unique_id,))
        self.dbConnection.commit()

        # Construct the INSERT INTO statement

        insert_sql = f"INSERT INTO t_document\
                (document_id , document_name, company_name,year,content_type,\
                    exp_pathway_keyword_search_completed_ind,internalization_keyword_search_completed_ind,\
                    mitigation_search_completed_ind,exp_insights_generated_ind,int_insights_generated_ind,\
                    int_exp_insights_generated, mitigation_exp_insights_generated,mitigation_int_insights_generated,\
                    mitigation_int_exp_insights_generated,added_dt,added_by ,modify_dt,modify_by, batch_id\
                )\
                VALUES\
                ({data_source_db_entity.unique_id},'{data_source_db_entity.document_name}','{data_source_db_entity.company_name}', {data_source_db_entity.year},{data_source_db_entity.content_type},\
                        0,0,0,0,0,0,0,0,0,NOW(), 'Mohan Hanumantha',NOW(), 'Mohan Hanumantha',{self.get_batch_id}\
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


# Commented out module-level execution to prevent startup errors
# data_src_mgr = DataSourceDBManager("Development")
# data_src_mgr.datafix_load_t_document_bulk()
