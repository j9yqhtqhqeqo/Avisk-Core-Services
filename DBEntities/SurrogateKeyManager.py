import psycopg2
import psycopg2.extras
import sys
from pathlib import Path
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

from Utilities.LoggingServices import logGenerator
from Utilities.Lookups import Lookups,DB_Connection
import pyodbc

PARM_LOGFILE = (
    r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Log/InsightGenLog/InsighDBtLog')
DEV_DB_CONNECTION_STRING = DB_Connection().DEV_DB_CONNECTION_STRING


key_word_hit_id =0
exp_pathway_unique_key: int
int_pathway_unique_key:int



def get_next_surrogate_key(save_type: int, database_context:str):
        connection_string =''

        if(database_context == 'Development'):
            connection_string = DEV_DB_CONNECTION_STRING
        elif(database_context == 'Test'):
            connection_string = TEST_DB_CONNECTION_STRING
        else:
            raise Exception("Database context Undefined")
        
        dbConnection = pyodbc.connect(connection_string)

        if (save_type == Lookups().Keyword_Hit_Save):
            if(key_word_hit_id > 1000):
                 key_word_hit_id = key_word_hit_id + 1
                 return key_word_hit_id
            else:
                sql = "select max(key_word_hit_id) from dbo.t_key_word_hits"
                cursor = dbConnection.cursor()
                cursor.execute(sql)
                key_word_hit_id = cursor.fetchone()[0] + 1
                cursor.close() 
                return key_word_hit_id

        elif (save_type == Lookups().Exposure_Save):
            sql = "select max(unique_key) from dbo.t_exposure_pathway_insights"
        elif (save_type == Lookups().Internalization_Save):
            sql = "select max(unique_key) from dbo.t_internalization_insights"
        # elif (save_type == Lookups().Mitigation_Exp_Insight_Type):
        #     sql = "select max(unique_key) from dbo.t_mitigation_exp_insights"
        # elif (save_type == Lookups().Mitigation_Int_Insight_Type):
        #     sql = "select max(unique_key) from dbo.t_mitigation_int_insights"
        # elif (save_type == Lookups().Exp_Int_Insight_Type):
        #     sql = "select max(unique_key) from dbo.t_exp_int_insights"
        # elif (save_type == Lookups().Mitigation_Exp_INT_Insight_Type):
        #     sql = "select max(unique_key) from dbo.t_mitigation_exp_int_insights"

        # cursor = self.dbConnection.cursor()
        # cursor.execute(sql)
        # current_db_seed = cursor.fetchone()[0]
        # cursor.close()
