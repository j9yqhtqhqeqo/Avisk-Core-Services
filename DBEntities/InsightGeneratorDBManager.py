import sys
from pathlib import Path
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

import pyodbc
import datetime as dt
from DBEntities.DocumentHeaderEntity import DocHeaderEntity
from DBEntities.DictionaryEntity import DictionaryEntity
from DBEntities.ProximityEntity import ProximityEntity
from DBEntities.ProximityEntity import KeyWordLocationsEntity
from Utilities.LoggingServices import logGenerator

PARM_LOGFILE = (r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Log/InsightGenLog/InsighDBtLog')



class InsightGeneratorDBManager:

    def __init__(self) -> None:
        self.dbConnection = pyodbc.connect(
            'DRIVER={ODBC Driver 18 for SQL Server};SERVER=earthdevdb.database.windows.net;UID=earthdevdbadmin@earthdevdb.database.windows.net;PWD=3q45yE3fEgQej8h!@;database=earth-dev')
        self.d_current_document_seed=0
        self.batch_id =0
        
        self.log_file_path = f'{PARM_LOGFILE} {dt.datetime.now().strftime("%c")}.txt'
        self.log_generator = logGenerator(self.log_file_path)


    def get_company_list(self, sic_code:None):#, company_name:None):

        company_list = []

        sic_code = sic_code+'%'
        # company_name = '%'+company_name+'%'

        sql = "SELECT sic.sic_code, sic.industry_title,header.conformed_name, header.form_type,header.document_id, header.document_name, header.reporting_year, header.reporting_quarter\
               FROM dbo.t_sic_codes sic INNER JOIN dbo.t_sec_document_header header ON sic.sic_code = header.sic_code_4_digit \
                    and header.reporting_year = 2022\
                    where sic.industry_title like ? \
                    and form_type ='10-K' and reporting_quarter =1\
                    order by sic.sic_code"

        # sql = "SELECT sic.sic_code, sic.industry_title,header.conformed_name, header.form_type,header.document_id, header.document_name, header.reporting_year, header.reporting_quarter\
        #        FROM dbo.t_sic_codes sic INNER JOIN dbo.t_sec_document_header header ON sic.sic_code = header.sic_code_4_digit \
        #             and header.reporting_year = 2022\
        #             where sic.industry_title like ? \
        #             and header.conformed_name like ? \
        #             and form_type ='10-K' and reporting_quarter =1\
        #             order by sic.sic_code"    

        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor()
            cursor.execute(sql, sic_code)#, company_name)
            rows = cursor.fetchall()
            for row in rows:
                # print(row.sic_code, ' ', row.industry_title, row.conformed_name, row.form_type,
                #       row.document_id, row.document_name, row.reporting_year, row.reporting_quarter)
                doc_header_entity = DocHeaderEntity()
                doc_header_entity.document_id = row.document_id
                doc_header_entity.document_name = row.document_name
                doc_header_entity.reporting_year = row.reporting_year
                doc_header_entity.reporting_quarter = row.reporting_quarter
                doc_header_entity.conformed_name = row.conformed_name
                doc_header_entity.sic_code = row.sic_code
                doc_header_entity.form_type = row.form_type
                company_list.append(doc_header_entity)
                # doc_header_entity.sic_code_4_digit = row.
                # doc_header_entity.irs_number  = row.
                # doc_header_entity.state_of_incorporation  = row.
                # doc_header_entity.fiscal_year_end  = row.

                # doc_header_entity.street_1  = row.
                # doc_header_entity.city  = row.
                # doc_header_entity.state  = row.
                # doc_header_entity.zip  = row.

            cursor.close()

            # print("Record inserted successfully!")

        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

        return company_list


    def get_company_id_by_Name(self,  company_name:None, reporting_year:None):

        company_id:int
        sql = "SELECT comp.company_id\
               FROM t_sec_company comp\
               where comp.conformed_name = ? \
                     and comp.reporting_year =?"

        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor()
            cursor.execute(sql, company_name,reporting_year)#, company_name)
            rows = cursor.fetchone()

            company_id = rows.company_id
            cursor.close()

            # print("Record inserted successfully!")

        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

        return company_id


    def get_int_dictionary_term_list(self):

        exp_dict_terms_list =[]    

        sql = "select d.dictionary_id,keywords,internalization_id from t_internalization_dictionary d \
                where d.dictionary_id <1015"
        
        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row in rows:
                exp_dict_terms_list.append(DictionaryEntity(row.dictionary_id,row.keywords, row.internalization_id))
            cursor.close()

        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

        return exp_dict_terms_list
        # return 'disturbance,efficiency,resiliance,supply,suppliers,inventory,disruptions,pandemic,capacity,over-reliance,logistics,products,production,regulations,trade,resilient,operations,materials,global,manufacturing,nearshoring,offshoring,volatility,collaboration,end-to-end,distribution,distributions,monitoring,regions,finances,weather,social ,unrest,policy,shifts,financial ,markets'
        

    def int_dictionary_terms():
        pass
    
    def getCurrentSeed(self):

        if(self.d_current_document_seed >= 1000):
            self.d_current_document_seed = self.d_current_document_seed+1
            return self.d_current_document_seed

        cursor = self.dbConnection.cursor()
        cursor.execute("select max(key_word_hit_id) from dbo.t_key_word_hits") 
        current_seed = cursor.fetchone()[0]
        if(current_seed):
            self.d_current_document_seed = current_seed+1
            return self.d_current_document_seed
        else:
            self.d_current_document_seed = 1001
            return self.d_current_document_seed
        cursor.close()

    def get_current_batch_id(self):

        if(self.batch_id>0): return self.batch_id

        cursor = self.dbConnection.cursor()
        cursor.execute("select max(batch_id) from dbo.t_key_word_hits") 
        batch_id = cursor.fetchone()[0]
        if(batch_id):
            self.batch_id = batch_id + 1
            return self.batch_id
        else:
            self.batch_id = 1
            return self.batch_id
        cursor.close()  

    def get_keyword_location_list(self):

        keyword_list =[]
        sql = 'select key_word_hit_id, key_word, locations, frequency from t_key_word_hits where insights_generated = 0 and document_id = 11 and dictionary_id = 1001'
        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor()
            cursor.execute(sql)#, company_name)
            rows = cursor.fetchall()
            for row in rows:
                # print(row.sic_code, ' ', row.industry_title, row.conformed_name, row.form_type,
                #       row.document_id, row.document_name, row.reporting_year, row.reporting_quarter)
                keyword_loc_entity = KeyWordLocationsEntity()
                keyword_loc_entity.key_word_hit_id = row.key_word_hit_id
                keyword_loc_entity.key_word = row.key_word
                keyword_loc_entity.locations = row.locations
                keyword_loc_entity.frequency = row.frequency
                
                keyword_list.append(keyword_loc_entity)
                # doc_header_entity.sic_code_4_digit = row.
                # doc_header_entity.irs_number  = row.
                # doc_header_entity.state_of_incorporation  = row.
                # doc_header_entity.fiscal_year_end  = row.

                # doc_header_entity.street_1  = row.
                # doc_header_entity.city  = row.
                # doc_header_entity.state  = row.
                # doc_header_entity.zip  = row.

            cursor.close()

            # print("Record inserted successfully!")

        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc
        
        return keyword_list


        pass

    def save_key_word_hits(self, proximity_entity_list, company_id:int,document_id:int, document_name:str, reporting_year:int, dictionary_type:int):

        proximity: ProximityEntity
        key_word_locations:KeyWordLocationsEntity
        total_records_added_to_db = 0
        for proximity in proximity_entity_list:
            dictionary_id = proximity.dictionary_id
            for key_word_locations in proximity.key_word_bunch:
                batch_id = self.get_current_batch_id()
                key_word_hit_id = self.getCurrentSeed()
                key_word = key_word_locations.key_word
                locations = key_word_locations.locations
                frequency = key_word_locations.frequency

                self.insert_key_word_hits_to_db (company_id,document_id, document_name,reporting_year,dictionary_id,key_word_hit_id, key_word, locations,frequency=frequency, dictionary_type=dictionary_type)
                total_records_added_to_db = total_records_added_to_db +1
            # Commit current batch 
            self.dbConnection.commit()
        self.log_generator.log_details("Total keyword location lists Added to the Database:"+ str(total_records_added_to_db))
        self.log_generator.log_details('################################################################################################')

        print("Total keyword location lists Added to the Database:"+ str(total_records_added_to_db))
        print('################################################################################################')


    def insert_key_word_hits_to_db(self, company_id:int, document_id:str, document_name:str, reporting_year:int,dictionary_id:int, key_word_hit_id:int, key_word:str, locations:str,frequency:int, dictionary_type:int):

        #reconfigure document id   
        new_doc_id =  int(str(self.batch_id)+str(document_id))
                
        # Create a cursor object to execute SQL queries
        cursor = self.dbConnection.cursor()
        # Construct the INSERT INTO statement

        sql = f"INSERT INTO dbo.t_key_word_hits( \
            batch_id, dictionary_type, key_word_hit_id , document_id,  document_name, company_id, reporting_year,\
            dictionary_id ,key_word, locations,frequency, insights_generated,\
            added_dt,added_by ,modify_dt,modify_by\
            )\
                VALUES\
                ({self.batch_id},{dictionary_type},{self.d_current_document_seed},{new_doc_id},N'{document_name}', {company_id}, {reporting_year},\
            {dictionary_id} ,N'{key_word}', N'{locations}', {frequency},0,  CURRENT_TIMESTAMP, N'Mohan Hanumantha',CURRENT_TIMESTAMP, N'Mohan Hanumantha')"
        try:
            # Execute the SQL query
            cursor.execute(sql)
            # self.dbConnection.commit()
        except Exception as exc:
            # Rollback the transaction if any error occurs
            self.dbConnection.rollback()
            print(f"Error: {str(exc)}")
            raise exc

        # Close the cursor and connection
        cursor.close()


        pass


    def save_insights(self):
        pass

    def remove_insights(self):
        pass

    def get_test_company_list(self):
        insightdbMgr = InsightGeneratorDBManager()
        return(insightdbMgr.get_company_list('Metal Mining', 'Lithium'))


# insightdbMgr = InsightGeneratorDBManager()
# exp_dict_terms = insightdbMgr.get_exp_dictionary_terms()

# for term in exp_dict_terms:
#     print(str(term.dictionary_id) + "    " + str(term.keywords))