import psycopg2.extras
import psycopg2
from DBEntities.DataSourceDBEntity import DataSourceDBEntity
from Utilities.Lookups import Lookups, Processing_Type, DB_Connection
import sys
from pathlib import Path
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))


# PostgreSQL connection for GCC environment
# Connection Timeout = 30

DEV_DB_CONNECTION_STRING = DB_Connection().DEV_DB_CONNECTION_STRING
# TEST_DB_CONNECTION_STRING = 'DRIVER={ODBC Driver 18 for SQL Server};SERVER=earthdevdb.database.windows.net;UID=earthdevdbadmin@earthdevdb.database.windows.net;PWD=3q45yE3fEgQej8h!@;database=earth-test'


class LookupsDBManager():

    def __init__(self, database_context: None) -> None:

        connection_string = ''

        if (database_context == 'Development'):
            connection_string = DEV_DB_CONNECTION_STRING
        elif (database_context == 'Test'):
            connection_string = TEST_DB_CONNECTION_STRING
        else:
            raise Exception("Database context Undefined")

        self.dbConnection = psycopg2.connect(connection_string)

    def get_exposure_pathway_search_status(self):
        status: str
        try:
            cursor = self.dbConnection.cursor()
            sql = "select data_lookups_description from t_data_lookups where data_lookups_group = %s"
            cursor.execute(sql, ('Exp_Keyword_Search_Mode',))
            rows = cursor.fetchone()
            status = rows[0]  # Access by index for PostgreSQL

        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

        return status

    def get_internalization_search_status(self):
        status: str
        try:
            cursor = self.dbConnection.cursor()
            sql = "select data_lookups_description from t_data_lookups where data_lookups_group = %s"
            cursor.execute(sql, ('Int_Keyword_Search_Mode',))
            rows = cursor.fetchone()
            status = rows[0]  # Access by index for PostgreSQL

        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

        return status

    def get_mitigation_search_status(self):
        status: str
        try:
            cursor = self.dbConnection.cursor()
            sql = "select data_lookups_description from t_data_lookups where data_lookups_group = %s"
            cursor.execute(sql, ('Mitigation_Keyword_Search_Mode',))
            rows = cursor.fetchone()
            status = rows[0]  # Access by index for PostgreSQL

        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

        return status

    def get_insight_gen_status(self, insight_gen_type: str):
        if (insight_gen_type == Lookups().Exposure_Pathway_Dictionary_Type):
            filter_condition = 'Exposure_Pathway_Insights'
        elif (insight_gen_type == Lookups().Internalization_Dictionary_Type):
            filter_condition = 'Internalization_Insights'
        elif (insight_gen_type == Lookups().Exp_Int_Insight_Type):
            filter_condition = 'Exp_Int_insights'

        elif (insight_gen_type == Lookups().Mitigation_Exp_Insight_Type):
            filter_condition = 'Mitigation_Exp_Insights'

        elif (insight_gen_type == Lookups().Mitigation_Int_Insight_Type):
            filter_condition = 'Mitigation_Int_insights'

        elif (insight_gen_type == Lookups().Mitigation_Exp_INT_Insight_Type):
            filter_condition = 'Mitigation_Exp_Int_insights'

        status: str
        try:
            cursor = self.dbConnection.cursor()
            sql = "select data_lookups_description from t_data_lookups where data_lookups_group = %s"
            cursor.execute(sql, (filter_condition,))
            rows = cursor.fetchone()
            status = rows[0]  # Access by index for PostgreSQL

        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

        return status

    def get_current_processing_status(self, processing_type: int):
        failedsql = 'EMPTY'

        if (processing_type == Processing_Type().KEYWORD_GEN_EXP):
            remainsql = f"select count(*) remaining_documents from t_document where exp_pathway_keyword_search_completed_ind = 0 and exp_validation_completed_ind = 1"
            failedsql = f"select count(*) failed_docs from t_document where exp_pathway_keyword_search_completed_ind =  2"

        if (processing_type == Processing_Type().KEYWORD_GEN_INT):
            remainsql = f"select count(*) remaining_documents from t_document where internalization_keyword_search_completed_ind = 0 and int_validation_completed_ind = 1"
            failedsql = f"select count(*) failed_docs from t_document where internalization_keyword_search_completed_ind = 2"

        if (processing_type == Processing_Type().KEYWORD_GEN_MIT):
            remainsql = f"select count(*) remaining_documents from t_document where mitigation_search_completed_ind = 0 and mit_validation_completed_ind = 1"
            failedsql = f"select count(*) failed_docs from t_document where mitigation_search_completed_ind = 2"

        if (processing_type == Processing_Type().EXPOSURE_INSIGHTS_GEN):
            remainsql = f"select count(*) remaining_documents from t_document where exp_insights_generated_ind = 0"
        if (processing_type == Processing_Type().INTERNALIZATION_INSIGHTS_GEN):
            remainsql = f"select count(*) remaining_documents from t_document where int_insights_generated_ind = 0"
        if (processing_type == Processing_Type().Exp_Int_Insight_GEN):
            remainsql = f"select count(*) remaining_documents from t_document where int_exp_insights_generated = 0"
        if (processing_type == Processing_Type().Mitigation_Exp_Insight_GEN):
            remainsql = f"select count(*) remaining_documents from t_document where mitigation_exp_insights_generated = 0"
        if (processing_type == Processing_Type().Mitigation_Int_Insight_GEN):
            remainsql = f"select count(*) remaining_documents from t_document where mitigation_int_insights_generated = 0"
        if (processing_type == Processing_Type().Mitigation_Exp_INT_Insight_GEN):
            remainsql = f"select count(*) remaining_documents from t_document where mitigation_int_exp_insights_generated = 0"

        remaining_documents = 0
        failed_documents = 0
        try:
            cursor = self.dbConnection.cursor()
            cursor.execute(remainsql)
            rows = cursor.fetchone()
            remaining_documents = rows[0]  # Access by index for PostgreSQL

            if (failedsql != 'EMPTY'):
                cursor.execute(failedsql)
                rows = cursor.fetchone()
                failed_documents = rows[0]  # Access by index for PostgreSQL

        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

        return failed_documents, remaining_documents
