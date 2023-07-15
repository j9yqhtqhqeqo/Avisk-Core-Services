import sys
from pathlib import Path
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

import pyodbc
import datetime as dt
from DBEntities.DocumentHeaderEntity import DocHeaderEntity
from DBEntities.DictionaryEntity import DictionaryEntity
from DBEntities.ProximityEntity import ProximityEntity
from DBEntities.ProximityEntity import KeyWordLocationsEntity
from DBEntities.ProximityEntity import  Insight
from DBEntities.ProximityEntity import DocumentEntity
from Utilities.Lookups import Lookups
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

        int_dict_terms_list =[]    

        sql = "select d.dictionary_id,keywords,internalization_id from t_internalization_dictionary d \
                where d.dictionary_id <= 1015"
        
        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row in rows:
                int_dict_terms_list.append(DictionaryEntity(dictionary_id=row.dictionary_id,keywords=row.keywords, internalization_id=row.internalization_id))
            cursor.close()

        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

        return int_dict_terms_list
    

    def get_exp_dictionary_term_list(self):

        exp_dict_terms_list =[]    

        sql = "select d.dictionary_id,d.keywords,d.exposure_path_id from t_exposure_pathway_dictionary d"
        
        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row in rows:
                exp_dict_terms_list.append(DictionaryEntity(dictionary_id= row.dictionary_id,keywords=row.keywords, exposure_pathway_id=row.exposure_path_id))
            cursor.close()

        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

        return exp_dict_terms_list
        

    def get_mitigation_dictionary_term_list(self):

        mitigation_dict_terms_list =[]    

        sql = "select dictionary_id,keywords from t_mitigation"
        
        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row in rows:
                mitigation_dict_terms_list.append(DictionaryEntity(dictionary_id=row.dictionary_id,keywords=row.keywords))
            cursor.close()

        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

        return mitigation_dict_terms_list
    

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

    def get_exp_pathway_document_list(self):
        document_list =[]
        try:
            cursor = self.dbConnection.cursor()
            cursor.execute("select doc.document_id, comp.company_id, doc.document_name, doc.company_name, doc.year \
                            from dbo.t_document doc, t_sec_company comp \
                            where \
                            doc.exp_pathway_keyword_search_completed_ind = 0 and doc.company_name = comp.conformed_name and doc.year = comp.reporting_year") 
            rows = cursor.fetchall()
            for row in rows:
                document_entity = DocumentEntity()
                document_entity.document_id = row.document_id
                document_entity.document_name = row.document_name    
                document_entity.company_name = row.company_name
                document_entity.company_id = row.company_id
                document_entity.year = row.year
                document_list.append(document_entity)
            cursor.close()
        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc
        
        return document_list

    def get_internalization_document_list(self):
        document_list =[]
        try:
            cursor = self.dbConnection.cursor()
            cursor.execute("select doc.document_id, comp.company_id, doc.document_name, doc.company_name, doc.year \
                            from dbo.t_document doc, t_sec_company comp \
                            where \
                            doc.internalization_keyword_search_completed_ind = 0 and doc.company_name = comp.conformed_name and doc.year = comp.reporting_year") 
            rows = cursor.fetchall()
            for row in rows:
                document_entity = DocumentEntity()
                document_entity.document_id = row.document_id
                document_entity.document_name = row.document_name    
                document_entity.company_name = row.company_name
                document_entity.company_id = row.company_id
                document_entity.year = row.year
                document_list.append(document_entity)
            cursor.close()
        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc
        
        return document_list

    def get_mitigation_document_list(self):
        document_list =[]
        try:
            cursor = self.dbConnection.cursor()
            cursor.execute("select doc.document_id, comp.company_id, doc.document_name, doc.company_name, doc.year \
                            from dbo.t_document doc, t_sec_company comp \
                            where \
                            doc.mitigation_search_completed_ind = 0 and doc.company_name = comp.conformed_name and doc.year = comp.reporting_year") 
            rows = cursor.fetchall()
            for row in rows:
                document_entity = DocumentEntity()
                document_entity.document_id = row.document_id
                document_entity.document_name = row.document_name    
                document_entity.company_name = row.company_name
                document_entity.company_id = row.company_id
                document_entity.year = row.year
                document_list.append(document_entity)
            cursor.close()
        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc
        
        return document_list

    def get_mitigation_exp_document_list(self):
        document_list =[]
        try:
            cursor = self.dbConnection.cursor()
            cursor.execute("select doc.document_id, comp.company_id, doc.document_name, doc.company_name, doc.year \
                            from dbo.t_document doc, t_sec_company comp \
                            where \
                            doc.mitigation_exp_insights_generated = 0 and doc.company_name = comp.conformed_name and doc.year = comp.reporting_year") 
            rows = cursor.fetchall()
            for row in rows:
                document_entity = DocumentEntity()
                document_entity.document_id = row.document_id
                document_entity.document_name = row.document_name    
                document_entity.company_name = row.company_name
                document_entity.company_id = row.company_id
                document_entity.year = row.year
                document_list.append(document_entity)
            cursor.close()
        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc
        
        return document_list

    def get_mitigation_lists(self, document_id):
       
        mitigation_keyword_list =[]
        sql = 'select document_id, key_word_hit_id, key_word,locations from t_key_word_hits where insights_generated = 0 and dictionary_type = 1002 and document_id = ?'
        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor()
            cursor.execute(sql, document_id)
            rows = cursor.fetchall()
            for row in rows:

                keyword_loc_entity = KeyWordLocationsEntity()
                keyword_loc_entity.key_word_hit_id = row.key_word_hit_id
                keyword_loc_entity.key_word = row.key_word
                keyword_loc_entity.locations = row.locations
                mitigation_keyword_list.append(keyword_loc_entity)

            cursor.close()

            # print("Record inserted successfully!")

        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc
        

        exp_keyword_list =[]
        sql = 'select document_id, key_word_hit_id, key_word,locations from t_key_word_hits where dictionary_type = 1000 and document_id = ?'
        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor()
            cursor.execute(sql, document_id)
            rows = cursor.fetchall()
            for row in rows:

                keyword_loc_entity = KeyWordLocationsEntity()
                keyword_loc_entity.key_word_hit_id = row.key_word_hit_id
                keyword_loc_entity.key_word = row.key_word
                keyword_loc_entity.locations = row.locations
                exp_keyword_list.append(keyword_loc_entity)

            cursor.close()

            # print("Record inserted successfully!")

        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc
        

        exp_insight_list =[]
        sql = 'select key_word_hit_id1, key_word_hit_id2, key_word1, key_word2 from t_exposure_pathway_insights where document_id = ? and score > 50'
        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor()
            cursor.execute(sql, document_id)
            rows = cursor.fetchall()
            for row in rows:

                insight_entity = Insight()
                insight_entity.keyword_hit_id1 = row.key_word_hit_id1
                insight_entity.keyword_hit_id2 = row.key_word_hit_id2
                insight_entity.keyword1 = row.key_word1
                insight_entity.keyword2 = row.key_word2
                exp_insight_list.append(insight_entity)

            cursor.close()

            # print("Record inserted successfully!")

        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc
        
        return mitigation_keyword_list,exp_keyword_list, exp_insight_list

    def get_keyword_location_list(self, batch_id=0, dictionary_type = 0, dictionary_id = 0, document_id = 0):

        keyword_list =[]
        sql = 'select key_word_hit_id, key_word, locations, frequency, dictionary_type, dictionary_id, document_id \
               from t_key_word_hits \
               where insights_generated = ? and batch_id = ? and dictionary_type =? and dictionary_id = ? and document_id =?\
               order by key_word_hit_id'
        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor()
            cursor.execute(sql, 0, batch_id, dictionary_type, dictionary_id, document_id)
            rows = cursor.fetchall()
            for row in rows:

                keyword_loc_entity = KeyWordLocationsEntity()
                keyword_loc_entity.key_word_hit_id = row.key_word_hit_id
                keyword_loc_entity.key_word = row.key_word
                keyword_loc_entity.locations = row.locations
                keyword_loc_entity.frequency = row.frequency
                keyword_loc_entity.dictionary_id = row.dictionary_id
                keyword_loc_entity.dictionary_type = row.dictionary_type
                
                keyword_list.append(keyword_loc_entity)

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
                
        # Create a cursor object to execute SQL queries
        cursor = self.dbConnection.cursor()
        # Construct the INSERT INTO statement

        sql = f"INSERT INTO dbo.t_key_word_hits( \
            batch_id, dictionary_type, key_word_hit_id , document_id,  document_name, company_id, reporting_year,\
            dictionary_id ,key_word, locations,frequency, insights_generated,\
            added_dt,added_by ,modify_dt,modify_by\
            )\
                VALUES\
                ({self.batch_id},{dictionary_type},{self.d_current_document_seed},{document_id},N'{document_name}', {company_id}, {reporting_year},\
            {dictionary_id} ,N'{key_word}', N'{locations}', {frequency},0,  CURRENT_TIMESTAMP, N'Mohan Hanumantha',CURRENT_TIMESTAMP, N'Mohan Hanumantha')"
        try:
            # Execute the SQL query
            cursor.execute(sql)
            # self.dbConnection.commit()
        except Exception as exc:
            # Rollback the transaction if any error occurs
            self.dbConnection.rollback()
            print("Error processing hits for word:" + key_word)
            print(f"Error: {str(exc)}")
            raise exc

        # Close the cursor and connection
        cursor.close()

        pass

    def update_exp_pathway_keyword_search_completed_ind(self, document_id):
         # Create a cursor object to execute SQL queries
        cursor = self.dbConnection.cursor()

        sql = f"update t_document set exp_pathway_keyword_search_completed_ind = 1 \
                ,modify_dt = CURRENT_TIMESTAMP ,modify_by = N'Mohan Hanumantha'\
                where document_id ={document_id}"
        try:
                # Execute the SQL query
                cursor.execute(sql)
                self.dbConnection.commit()
        except Exception as exc:
                # Rollback the transaction if any error occurs
                self.dbConnection.rollback()
                print(f"Error: {str(exc)}")
                raise exc

        # Close the cursor and connection
        cursor.close()

    def update_internalization_keyword_search_completed_ind(self, document_id):
         # Create a cursor object to execute SQL queries
        cursor = self.dbConnection.cursor()

        sql = f"update t_document set internalization_keyword_search_completed_ind = 1 \
                ,modify_dt = CURRENT_TIMESTAMP ,modify_by = N'Mohan Hanumantha'\
                where document_id ={document_id}"
        try:
                # Execute the SQL query
                cursor.execute(sql)
                self.dbConnection.commit()
        except Exception as exc:
                # Rollback the transaction if any error occurs
                self.dbConnection.rollback()
                print(f"Error: {str(exc)}")
                raise exc

        # Close the cursor and connection
        cursor.close()

    def update_mitigation_keyword_search_completed_ind(self, document_id):
         # Create a cursor object to execute SQL queries
        cursor = self.dbConnection.cursor()

        sql = f"update t_document set mitigation_search_completed_ind = 1 \
                ,modify_dt = CURRENT_TIMESTAMP ,modify_by = N'Mohan Hanumantha'\
                where document_id ={document_id}"
        try:
                # Execute the SQL query
                cursor.execute(sql)
                self.dbConnection.commit()
        except Exception as exc:
                # Rollback the transaction if any error occurs
                self.dbConnection.rollback()
                print(f"Error: {str(exc)}")
                raise exc

        # Close the cursor and connection
        cursor.close()


    def get_unprocessed_document_items(self, dictionary_type = 0):

        document_list =[]
        sql = 'select distinct document_id, dictionary_id, document_name, batch_id,dictionary_type from t_key_word_hits where insights_generated = 0 and dictionary_type = ? order by dictionary_id'
        try:
            # Execute the SQL query
            cursor = self.dbConnection.cursor()
            cursor.execute(sql, dictionary_type)
            rows = cursor.fetchall()
            for row in rows:
                keyword_loc_entity = KeyWordLocationsEntity()
                keyword_loc_entity.dictionary_id = row.dictionary_id
                keyword_loc_entity.document_id = row.document_id
                keyword_loc_entity.document_name = row.document_name
                keyword_loc_entity.batch_id = row.batch_id
                keyword_loc_entity.dictionary_type = row.dictionary_type
                document_list.append(keyword_loc_entity)
            cursor.close()

        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc
        
        return document_list

    def save_insights(self, insightList, dictionary_type):
        insight: Insight
    
        total_records_added_to_db = 0
        for insight in insightList:
            key_word_hit_id1 = insight.keyword_hit_id1
            key_word_hit_id2 = insight.keyword_hit_id2
            key_word1 = insight.keyword1
            key_word2 = insight.keyword2
            factor1 = insight.factor1
            factor2 = insight.factor2
            score = insight.score
            document_name = insight.document_name
            document_id = insight.document_id
  
            # Create a cursor object to execute SQL queries
            cursor = self.dbConnection.cursor()
            # Construct the INSERT INTO statement

            if(dictionary_type == Lookups().Internalization_Dictionary_Type):
                sql = f"INSERT INTO dbo.t_internalization_insights( \
                    document_id, document_name, key_word_hit_id1, key_word_hit_id2,key_word1, key_word2,score,\
                    factor1, factor2, added_dt,added_by ,modify_dt,modify_by\
                    )\
                        VALUES\
                        ({document_id},N'{document_name}',{key_word_hit_id1},{key_word_hit_id2},N'{key_word1}',N'{key_word2}',{score},\
                        {factor1}, {factor2},CURRENT_TIMESTAMP, N'Mohan Hanumantha',CURRENT_TIMESTAMP, N'Mohan Hanumantha')"

            elif(dictionary_type == Lookups().Exposure_Pathway_Dictionary_Type):
                sql = f"INSERT INTO dbo.t_exposure_pathway_insights( \
                    document_id, document_name, key_word_hit_id1, key_word_hit_id2,key_word1, key_word2,score,\
                    factor1, factor2, added_dt,added_by ,modify_dt,modify_by\
                    )\
                        VALUES\
                        ({document_id},N'{document_name}',{key_word_hit_id1},{key_word_hit_id2},N'{key_word1}',N'{key_word2}',{score},\
                        {factor1}, {factor2},CURRENT_TIMESTAMP, N'Mohan Hanumantha',CURRENT_TIMESTAMP, N'Mohan Hanumantha')"    

            try:
                # Execute the SQL query
                cursor.execute(sql)
                total_records_added_to_db = total_records_added_to_db +1 
                if(total_records_added_to_db % 50 == 0):
                    self.dbConnection.commit()

            except Exception as exc:
                # Rollback the transaction if any error occurs
                self.dbConnection.rollback()
                print(f"Error: {str(exc)}")
                raise exc

        # Close the cursor and connection
        self.dbConnection.commit()
        cursor.close()

        # self.dbConnection.commit()
        self.log_generator.log_details("Total Insights added to the Database:"+ str(total_records_added_to_db))
        self.log_generator.log_details('################################################################################################')

        print("Total Insights added to the Database:"+ str(total_records_added_to_db))

    def update_insights_generated_batch(self, batch_id =0, dictionary_type = 0, dictionary_id = 0, document_id =0):
        # Create a cursor object to execute SQL queries
        cursor = self.dbConnection.cursor()

        sql = f"update t_key_word_hits set \
                insights_generated = 1 ,modify_dt = CURRENT_TIMESTAMP ,modify_by = N'Mohan Hanumantha'\
                where batch_id ={batch_id} and insights_generated = 0 and dictionary_type ={dictionary_type} and dictionary_id ={dictionary_id} and document_id ={document_id}"
        try:
                # Execute the SQL query
                cursor.execute(sql)
                self.dbConnection.commit()
        except Exception as exc:
                # Rollback the transaction if any error occurs
                self.dbConnection.rollback()
                print(f"Error: {str(exc)}")
                raise exc

        # Close the cursor and connection
        cursor.close()


    def remove_insights(self):
        pass

    def get_test_company_list(self):
        insightdbMgr = InsightGeneratorDBManager()
        return(insightdbMgr.get_company_list('Metal Mining', 'Lithium'))


# insightdbMgr = InsightGeneratorDBManager()
# exp_dict_terms = insightdbMgr.get_exp_dictionary_terms()

# for term in exp_dict_terms:
#     print(str(term.dictionary_id) + "    " + str(term.keywords))