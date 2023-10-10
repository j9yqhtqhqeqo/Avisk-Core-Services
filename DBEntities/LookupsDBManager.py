import pyodbc
import sys
from pathlib import Path
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))
from DBEntities.DataSourceDBEntity import DataSourceDBEntity

DEV_DB_CONNECTION_STRING = 'DRIVER={ODBC Driver 18 for SQL Server};SERVER=earthdevdb.database.windows.net;UID=earthdevdbadmin@earthdevdb.database.windows.net;PWD=3q45yE3fEgQej8h!@;database=earth-dev'
TEST_DB_CONNECTION_STRING = 'DRIVER={ODBC Driver 18 for SQL Server};SERVER=earthdevdb.database.windows.net;UID=earthdevdbadmin@earthdevdb.database.windows.net;PWD=3q45yE3fEgQej8h!@;database=earth-test'


class LookupsDBManager():

    def __init__(self, database_context:None) -> None:

        connection_string =''

        if(database_context == 'Development'):
            connection_string = DEV_DB_CONNECTION_STRING
        elif(database_context == 'Test'):
            connection_string = TEST_DB_CONNECTION_STRING
        else:
            raise Exception("Database context Undefined")
        
        self.dbConnection = pyodbc.connect(connection_string)


    def get_exposure_pathway_search_status(self):
        status:str
        try:
            cursor = self.dbConnection.cursor()
            sql = "select data_lookups_description from t_data_lookups where data_lookups_group = ?"
            cursor.execute(sql, 'Exp_Keyword_Search_Mode')
            rows = cursor.fetchone()
            status = rows.data_lookups_description
            
        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

        return status

    def get_internalization_search_status(self):
        status:str
        try:
            cursor = self.dbConnection.cursor()
            sql = "select data_lookups_description from t_data_lookups where data_lookups_group = ?"
            cursor.execute(sql, 'Int_Keyword_Search_Mode')
            rows = cursor.fetchone()
            status = rows.data_lookups_description
            
        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

        return status
    
    def get_mitigation_search_status(self):
        status:str
        try:
            cursor = self.dbConnection.cursor()
            sql = "select data_lookups_description from t_data_lookups where data_lookups_group = ?"
            cursor.execute(sql, 'Mitigation_Keyword_Search_Mode')
            rows = cursor.fetchone()
            status = rows.data_lookups_description
            
        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

        return status