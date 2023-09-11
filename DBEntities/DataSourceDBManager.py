import pyodbc
import sys
from pathlib import Path
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))
from DBEntities.DataSourceDBEntity import DataSourceDBEntity


class DataSourceDBManager():

    def __init__(self) -> None:
        super().__init__()
        self.dbConnection = pyodbc.connect(
            'DRIVER={ODBC Driver 18 for SQL Server};SERVER=earthdevdb.database.windows.net;UID=earthdevdbadmin@earthdevdb.database.windows.net;PWD=3q45yE3fEgQej8h!@;database=earth-dev')

    #Get unprocessed data source List
    def get_unprocessed_content_list(self):
        document_list = []
        try:
            cursor = self.dbConnection.cursor()
            cursor.execute(" select d.unique_id ,d.company_name ,d.year ,d.content_type,l.data_lookups_description, d.source_type , d.source_url ,d.processed_ind \
                            from t_data_source d INNER join  t_data_lookups l on d.content_type = l.data_lookups_id\
                            where d.processed_ind = 0 order by d.unique_id")
            rows = cursor.fetchall()
            for row in rows:
                document_entity = DataSourceDBEntity(
                unique_id = row.unique_id,
                company_name = row.company_name,
                year = row.year,
                content_type=row.content_type,
                content_type_desc=row.data_lookups_description,
                source_type = row.source_type,
                source_url = row.source_url,
                processed_ind=row.processed_ind
                )
                document_list.append(document_entity)
            cursor.close()
        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

        return document_list

    def add_stage1_processed_files_to_t_document(self, document_list=None):
        data_source_db_entity: DataSourceDBEntity
        
        total_records_added_to_db = 0
        for data_source_db_entity in document_list:

            # Create a cursor object to execute SQL queries
            cursor = self.dbConnection.cursor()
            # Construct the INSERT INTO statement

            insert_sql = f"INSERT INTO dbo.t_document\
                    (document_id , document_name, company_name,year,content_type,\
                        exp_pathway_keyword_search_completed_ind,internalization_keyword_search_completed_ind,\
                        mitigation_search_completed_ind,exp_insights_generated_ind,int_insights_generated_ind,\
                        int_exp_insights_generated, mitigation_exp_insights_generated,mitigation_int_insights_generated,\
                        mitigation_int_exp_insights_generated,added_dt,added_by ,modify_dt,modify_by\
                    )\
                    VALUES\
                    ({data_source_db_entity.unique_id},N'{data_source_db_entity.document_name}',N'{data_source_db_entity.company_name}', {data_source_db_entity.year},{data_source_db_entity.content_type},\
                            0,0,0,0,0,0,0,0,0,CURRENT_TIMESTAMP, N'Mohan Hanumantha',CURRENT_TIMESTAMP, N'Mohan Hanumantha'\
                    )"
            
            update_sql = f"update t_data_source set processed_ind = 1, modify_dt = CURRENT_TIMESTAMP where unique_id = {data_source_db_entity.unique_id}"

            try:
                # Execute the SQL query
                cursor.execute(insert_sql)
                total_records_added_to_db = total_records_added_to_db +1 

                cursor.execute(update_sql)

                if(total_records_added_to_db % 50 == 0):
                    self.dbConnection.commit()

            except Exception as exc:
                # Rollback the transaction if any error occurs
                self.dbConnection.rollback()
                print(f"Error: {str(exc)}")
                raise exc
                       
            if(total_records_added_to_db % 50 == 0):
                print("Datasource records processed  So far...:"+ str(total_records_added_to_db))

        # Close the cursor and connection
        self.dbConnection.commit()
        cursor.close()
        print("Total Datasource records processed:"+ str(total_records_added_to_db))


    def update_data_source_processed_indicator(self, document_list=None):
        pass