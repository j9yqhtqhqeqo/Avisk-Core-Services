import psycopg2.extras
import psycopg2
import sys
from pathlib import Path
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

import pyodbc
import datetime as dt
import re
from Utilities.Lookups import Lookups,DB_Connection
from DocumentHeaderEntity import DocHeaderEntity


class DocumentDBManager():

    def __init__(self) -> None:
        super().__init__()
        self.d_current_document_seed=0
        self.b_load_document_seed_from_db = True
        self.dbConnection = pyodbc.connect(DB_Connection().DEV_DB_CONNECTION_STRING)
        self.current_count:int
        
    def getCurrentDocumentSeed(self):
        if(self.b_load_document_seed_from_db):
            cursor = self.dbConnection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("select max(document_id) from dbo.t_sec_document_header") 
            current_seed = cursor.fetchone()[0]
            if(current_seed):
                self.b_load_document_seed_from_db =False
                self.d_current_document_seed = current_seed+1
                return self.d_current_document_seed
            else:
                return 1000
            cursor.close()
        else:
            self.d_current_document_seed +=1
            return self.d_current_document_seed

    def saveDocumentHeader(self, doc_header: DocHeaderEntity):
        
        self.d_current_document_seed = self.getCurrentDocumentSeed()

        conn = pyodbc.connect('DRIVER={ODBC Driver 18 for SQL Server};SERVER=earthdevdb.database.windows.net;UID=earthdevdbadmin@earthdevdb.database.windows.net;PWD=3q45yE3fEgQej8h!@;database=earth-dev')
    
        # Create a cursor object to execute SQL queries
        cursor = conn.cursor()
        # Construct the INSERT INTO statement

  
        sql = f"INSERT INTO dbo.t_sec_document_header( \
            document_id ,  reporting_year, reporting_quarter, document_name,\
            conformed_name ,sic_code, irs_number, state_of_incorporation ,fiscal_year_end ,form_type,street_1,city ,state , zip,\
            added_dt,added_by ,modify_dt,modify_by\
            )\
                VALUES\
                ({self.d_current_document_seed},{doc_header.d_reporting_year},{doc_header.d_reporting_quarter},N'{doc_header.f_document_name}',\
                N'{doc_header.conformed_name}', N'{doc_header.standard_industry_classification}', {doc_header.irs_number} ,N'{doc_header.state_of_incorporation}',\
                N'{doc_header.fiscal_year_end}', N'{doc_header.form_type}', N'{doc_header.street_1}',N'{doc_header.city}', N'{doc_header.state}',N'{doc_header.zip}',\
                CURRENT_TIMESTAMP, N'Mohan Hanumantha',CURRENT_TIMESTAMP, N'Mohan Hanumantha')"
        try:
            # Execute the SQL query
            cursor.execute(sql)

            # Commit the transaction
            conn.commit()

            print("Record inserted successfully!")
        except Exception as exc:
            # Rollback the transaction if any error occurs
            conn.rollback()
            print(f"Error: {str(exc)}")
            raise exc

        # Close the cursor and connection
        cursor.close()
        conn.close()
        return self.d_current_document_seed

    # def updateValidationFileGenerated(self, Dictionary_Type:int):

    #     if(Dictionary_Type == Lookups().Exposure_Pathway_Dictionary_Type):
    #         ##
    #         sql = "update t_exposure_pathway_insights set score_normalized = (score * 100)/(select max(score) from t_exposure_pathway_insights where document_id = %s) where document_id = %s"

    #     elif(Dictionary_Type == Lookups().Internalization_Dictionary_Type):
    #         ##
    #         pass
    #     elif(Dictionary_Type == Lookups().Mitigation_Dictionary_Type):
    #         pass

    #     cursor = self.dbConnection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    #     cursor.execute(sql, document_id, document_id)
    #     self.dbConnection.commit()

    #     cursor.close()