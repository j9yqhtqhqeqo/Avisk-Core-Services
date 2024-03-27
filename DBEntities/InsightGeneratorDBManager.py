from DBEntities.DashboardDBEntitties import SectorYearDBEntity, Reporting_DB_Entity
from Utilities.LoggingServices import logGenerator
from Utilities.Lookups import Lookups
from DBEntities.ProximityEntity import DocumentEntity
from DBEntities.ProximityEntity import ExpIntInsight
from DBEntities.ProximityEntity import MitigationExpIntInsight
from DBEntities.ProximityEntity import Insight
from DBEntities.ProximityEntity import KeyWordLocationsEntity
from DBEntities.ProximityEntity import ProximityEntity
from DBEntities.DictionaryEntity import DictionaryEntity
from DBEntities.DocumentHeaderEntity import DocHeaderEntity
import datetime as dt
import pyodbc
import sys
from pathlib import Path
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))


INSIGHT_SCORE_THRESHOLD = 10
EXP_INT_MITIGATION_THRESHOLD = 10


PARM_LOGFILE = (
    r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Log/InsightGenLog/InsighDBtLog')
DEV_DB_CONNECTION_STRING = 'DRIVER={ODBC Driver 18 for SQL Server};SERVER=earthdevdb.database.windows.net;UID=earthdevdbadmin@earthdevdb.database.windows.net;PWD=3q45yE3fEgQej8h!@;database=earth-dev'
TEST_DB_CONNECTION_STRING = 'DRIVER={ODBC Driver 18 for SQL Server};SERVER=earthdevdb.database.windows.net;UID=earthdevdbadmin@earthdevdb.database.windows.net;PWD=3q45yE3fEgQej8h!@;database=earth-test'
DB_LOGGING_ENABLED = False


class InsightGeneratorDBManager:

    # COMMON

    def __init__(self, database_context: None) -> None:

        connection_string = ''

        if (database_context == 'Development'):
            connection_string = DEV_DB_CONNECTION_STRING
        elif (database_context == 'Test'):
            connection_string = TEST_DB_CONNECTION_STRING
        else:
            raise Exception("Database context Undefined")

        self.dbConnection = pyodbc.connect(connection_string)

        self.d_next_seed = 0
        self.batch_id = 0

        self.log_file_path = f'{PARM_LOGFILE} {dt.datetime.now().strftime("%c")}.txt'
        self.log_generator = logGenerator(self.log_file_path)

    def get_company_list(self, sic_code: None):  # , company_name:None):

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
            cursor.execute(sql, sic_code)  # , company_name)
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

    def get_company_id_by_Name(self,  company_name: None, reporting_year: None):

        company_id: int
        sql = "SELECT comp.company_id\
               FROM t_sec_company comp\
               where comp.conformed_name = ? \
                     and comp.reporting_year =?"

        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor()
            # , company_name)
            cursor.execute(sql, company_name, reporting_year)
            rows = cursor.fetchone()

            company_id = rows.company_id
            cursor.close()

            # print("Record inserted successfully!")

        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

        return company_id

    def get_next_surrogate_key(self, save_type: int):

        if (self.d_next_seed >= 1000):
            self.d_next_seed = self.d_next_seed+1
            return self.d_next_seed

        if (save_type == Lookups().Exposure_Save):
            sql = "select max(unique_key) from dbo.t_exposure_pathway_insights"
        elif (save_type == Lookups().Internalization_Save):
            sql = "select max(unique_key) from dbo.t_internalization_insights"
        elif (save_type == Lookups().Mitigation_Exp_Insight_Type):
            sql = "select max(unique_key) from dbo.t_mitigation_exp_insights"
        elif (save_type == Lookups().Mitigation_Int_Insight_Type):
            sql = "select max(unique_key) from dbo.t_mitigation_int_insights"
        elif (save_type == Lookups().Exp_Int_Insight_Type):
            sql = "select max(unique_key) from dbo.t_exp_int_insights"
        elif (save_type == Lookups().Mitigation_Exp_INT_Insight_Type):
            sql = "select max(unique_key) from dbo.t_mitigation_exp_int_insights"

        cursor = self.dbConnection.cursor()

        cursor.execute(sql)

        current_db_seed = cursor.fetchone()[0]
        if (current_db_seed):
            self.d_next_seed = current_db_seed+1
            return self.d_next_seed
        else:
            self.d_next_seed = 1001
            return self.d_next_seed
        cursor.close()

    def normalize_document_score(self,  dictionary_type: int, document_id: int):

        if (dictionary_type == Lookups().Exposure_Pathway_Dictionary_Type):
            sql = "update t_exposure_pathway_insights set score_normalized = (score * 100)/(select max(score) from t_exposure_pathway_insights where document_id = ?) where document_id = ?"
        elif (dictionary_type == Lookups().Internalization_Dictionary_Type):
            sql = "update t_internalization_insights set score_normalized = (score * 100)/(select max(score) from t_internalization_insights where document_id = ?) where document_id = ?"
        elif (dictionary_type == Lookups().Mitigation_Exp_Insight_Type):
            sql = "update t_mitigation_exp_insights set score_normalized = (score * 100)/(select max(score) from t_mitigation_exp_insights where document_id = ?) where document_id = ?"
        elif (dictionary_type == Lookups().Mitigation_Int_Insight_Type):
            sql = "update t_mitigation_int_insights set score_normalized = (score * 100)/(select max(score) from t_mitigation_int_insights where document_id = ?) where document_id = ?"
        elif (dictionary_type == Lookups().Exp_Int_Insight_Type):
            sql = "update t_exp_int_insights set score_normalized = (score * 100)/(select max(score) from t_exp_int_insights where document_id = ?) where document_id = ?"
        elif (dictionary_type == Lookups().Mitigation_Exp_INT_Insight_Type):
            sql = "update t_mitigation_exp_int_insights set score_normalized = (score * 100)/(select max(score) from t_mitigation_exp_int_insights where document_id = ?) where document_id = ?"

        cursor = self.dbConnection.cursor()

        cursor.execute(sql, document_id, document_id)
        self.dbConnection.commit()

        cursor.close()

    def get_keyword_location_list(self, dictionary_type=0, dictionary_id=0, document_id=0):

        keyword_list = []
        sql = 'select key_word_hit_id, key_word, locations, frequency, dictionary_type, dictionary_id, document_id, exposure_path_id, internalization_id \
               from t_key_word_hits \
               where dictionary_type =? and dictionary_id = ? and document_id =?\
               order by key_word_hit_id'
        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor()
            cursor.execute(sql, dictionary_type,
                           dictionary_id, document_id)
            rows = cursor.fetchall()
            for row in rows:

                keyword_loc_entity = KeyWordLocationsEntity()
                keyword_loc_entity.key_word_hit_id = row.key_word_hit_id
                keyword_loc_entity.key_word = row.key_word
                keyword_loc_entity.locations = row.locations
                keyword_loc_entity.frequency = row.frequency
                keyword_loc_entity.dictionary_id = row.dictionary_id
                keyword_loc_entity.dictionary_type = row.dictionary_type
                keyword_loc_entity.exposure_path_id = row.exposure_path_id
                keyword_loc_entity.internalization_id = row.internalization_id

                keyword_list.append(keyword_loc_entity)

            cursor.close()

            # print("Record inserted successfully!")

        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

        return keyword_list

        pass

    def get_unprocessed_document_items_for_insight_gen(self, dictionary_type=0):

        document_list = []

        if (dictionary_type == Lookups().Exposure_Pathway_Dictionary_Type):
            sql = 'select doc.document_id, doc.year \
                from  t_document doc where doc.exp_insights_generated_ind = 0\
                order by document_id'
        elif (dictionary_type == Lookups().Internalization_Dictionary_Type):
            sql = 'select doc.document_id, doc.year \
                from  t_document doc where doc.int_insights_generated_ind = 0\
                order by document_id'
        try:
            # Execute the SQL query
            cursor = self.dbConnection.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row in rows:
                keyword_loc_entity = KeyWordLocationsEntity()
                keyword_loc_entity.document_id = row.document_id
                keyword_loc_entity.year = row.year
                document_list.append(keyword_loc_entity)
            cursor.close()

        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

        return document_list

    def get_keyword_hits_for_insight_gen(self, dictionary_type: int, document_id: int):

        document_keyword_list = []

        sql = f"select distinct hits.document_id, hits.dictionary_id, hits.document_name,hits.dictionary_type \
            from t_key_word_hits hits \
            where  hits.dictionary_type = ? and hits.document_id = ?"
        try:
            # Execute the SQL query
            cursor = self.dbConnection.cursor()
            cursor.execute(sql, dictionary_type, document_id)
            rows = cursor.fetchall()
            for row in rows:
                keyword_loc_entity = KeyWordLocationsEntity()
                keyword_loc_entity.dictionary_id = row.dictionary_id
                keyword_loc_entity.document_id = row.document_id
                keyword_loc_entity.document_name = row.document_name
                keyword_loc_entity.dictionary_type = row.dictionary_type
                document_keyword_list.append(keyword_loc_entity)
            cursor.close()

        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

        return document_keyword_list

    def insert_key_word_hits_to_db(self, company_id: int, document_id: str, document_name: str, reporting_year: int, dictionary_id: int, key_word: str, locations: str, frequency: int, dictionary_type: int, exposure_path_id: int, internalization_id: int, impact_category_id: int, esg_category_id: int, batch_id: int):

        # Create a cursor object to execute SQL queries
        cursor = self.dbConnection.cursor()
        # Construct the INSERT INTO statement

        sql = f"INSERT INTO dbo.t_key_word_hits( \
                dictionary_type, document_id,  document_name, company_id, reporting_year,batch_id,\
                dictionary_id ,key_word, locations,frequency, insights_generated,exposure_path_id, internalization_id,\
                impact_category_id, esg_category_id,\
                added_dt,added_by ,modify_dt,modify_by\
                )\
                    VALUES\
                ({dictionary_type},{document_id},N'{document_name}', {company_id}, {reporting_year},{batch_id},\
                {dictionary_id} ,N'{key_word}', N'{locations}', {frequency},0, {exposure_path_id}, {internalization_id},\
                {impact_category_id},{esg_category_id},\
                CURRENT_TIMESTAMP, N'Mohan Hanumantha',CURRENT_TIMESTAMP, N'Mohan Hanumantha')"
        try:
            # Execute the SQL query
            cursor.execute(sql)
            # self.dbConnection.commit()
        except Exception as exc:
            # Rollback the transaction if any error occurs
            self.dbConnection.rollback()
            print("Error processing hits for word:" +
                  key_word + " , Document ID:"+str(document_id))
            # print('Location Size:'+ str(len(locations)))
            # print(locations)
            print(f"Error: {str(exc)}")
            raise exc

        # Close the cursor and connection
        cursor.close()

        pass

    def save_insights(self, insightList, dictionary_type, year=0):
        insight: Insight
        self.d_next_seed = 0
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
            exposure_path_id = insight.exposure_path_id
            internalization_id = insight.internalization_id

            # Create a cursor object to execute SQL queries
            cursor = self.dbConnection.cursor()
            # Construct the INSERT INTO statement

            if (dictionary_type == Lookups().Exposure_Pathway_Dictionary_Type):
                sql = f"INSERT INTO dbo.t_exposure_pathway_insights( \
                     document_id, document_name, key_word_hit_id1, key_word_hit_id2,key_word1, key_word2,score,\
                    factor1, factor2,exposure_path_id, added_dt,added_by ,modify_dt,modify_by, year\
                    )\
                        VALUES\
                        ({document_id},N'{document_name}',{key_word_hit_id1},{key_word_hit_id2},N'{key_word1}',N'{key_word2}',{score},\
                        {factor1}, {factor2},{exposure_path_id},CURRENT_TIMESTAMP, N'Mohan Hanumantha',CURRENT_TIMESTAMP, N'Mohan Hanumantha',{year})"

            elif (dictionary_type == Lookups().Internalization_Dictionary_Type):
                sql = f"INSERT INTO dbo.t_internalization_insights( \
                    document_id, document_name, key_word_hit_id1, key_word_hit_id2,key_word1, key_word2,score,\
                    factor1, factor2,internalization_id, added_dt,added_by ,modify_dt,modify_by, year\
                    )\
                        VALUES\
                        ({document_id},N'{document_name}',{key_word_hit_id1},{key_word_hit_id2},N'{key_word1}',N'{key_word2}',{score},\
                        {factor1}, {factor2},{internalization_id},CURRENT_TIMESTAMP, N'Mohan Hanumantha',CURRENT_TIMESTAMP, N'Mohan Hanumantha',{year})"

            elif (dictionary_type == Lookups().Mitigation_Exp_Insight_Type):
                mitigation_keyword_hit_id = insight.mitigation_keyword_hit_id
                mitigation_keyword = insight.mitigation_keyword
                # int_unique_key = self.get_next_surrogate_key(
                #     Lookups().Mitigation_Exp_Insight_Type)

                sql = f"INSERT INTO dbo.t_mitigation_exp_insights( \
                    document_id, document_name, key_word_hit_id1, key_word_hit_id2,key_word1, key_word2,mitigation_keyword_hit_id,mitigation_keyword,\
                    score,factor1, factor2, exposure_path_id,added_dt,added_by ,modify_dt,modify_by,year\
                    )\
                        VALUES\
                        ({document_id},N'{document_name}',{key_word_hit_id1},{key_word_hit_id2},N'{key_word1}',N'{key_word2}',{mitigation_keyword_hit_id},N'{mitigation_keyword}',\
                        {score},{factor1}, {factor2},{exposure_path_id},CURRENT_TIMESTAMP, N'Mohan Hanumantha',CURRENT_TIMESTAMP, N'Mohan Hanumantha',{year})"

            elif (dictionary_type == Lookups().Mitigation_Int_Insight_Type):
                mitigation_keyword_hit_id = insight.mitigation_keyword_hit_id
                mitigation_keyword = insight.mitigation_keyword
                # int_unique_key = self.get_next_surrogate_key(
                #     Lookups().Mitigation_Int_Insight_Type)

                sql = f"INSERT INTO dbo.t_mitigation_int_insights( \
                     document_id, document_name, key_word_hit_id1, key_word_hit_id2,key_word1, key_word2,mitigation_keyword_hit_id,mitigation_keyword,\
                    score,factor1, factor2, internalization_id, added_dt,added_by ,modify_dt,modify_by, year\
                    )\
                        VALUES\
                        ({document_id},N'{document_name}',{key_word_hit_id1},{key_word_hit_id2},N'{key_word1}',N'{key_word2}',{mitigation_keyword_hit_id},N'{mitigation_keyword}',\
                        {score},{factor1}, {factor2},{internalization_id},CURRENT_TIMESTAMP, N'Mohan Hanumantha',CURRENT_TIMESTAMP, N'Mohan Hanumantha',{year})"

            try:
                # Execute the SQL query
                cursor.execute(sql)
                total_records_added_to_db = total_records_added_to_db + 1
                if (total_records_added_to_db % 50 == 0):
                    self.dbConnection.commit()

            except Exception as exc:
                # Rollback the transaction if any error occurs
                self.dbConnection.rollback()
                print(f"Error: {str(exc)}")
                raise exc

            # if (total_records_added_to_db % 250 == 0):
            #     print("Insights added to the Database So far...:" +
            #           str(total_records_added_to_db))

        # Close the cursor and connection
        if (total_records_added_to_db > 0):
            self.dbConnection.commit()
            cursor.close()

        # self.dbConnection.commit()
        if (DB_LOGGING_ENABLED):
            self.log_generator.log_details(
                "Total Insights added to the Database:" + str(total_records_added_to_db))
            self.log_generator.log_details(
                '################################################################################################')

        # print("Total Insights added to the Database:" +
        #       str(total_records_added_to_db))

    def cleanup_insights_for_document(self, dictionary_type, document_id):

        cursor = self.dbConnection.cursor()
        if (dictionary_type == Lookups().Exposure_Pathway_Dictionary_Type):
            sql = f"delete dbo.t_exposure_pathway_insights where document_id = ?"

        elif (dictionary_type == Lookups().Internalization_Dictionary_Type):
            int_unique_key = self.get_next_surrogate_key(
                Lookups().Internalization_Save)
            sql = f"delete dbo.t_internalization_insights where document_id = ?"

        elif (dictionary_type == Lookups().Exp_Int_Insight_Type):
            sql = f"delete  dbo.t_exp_int_insights where document_id = ?"

        elif (dictionary_type == Lookups().Mitigation_Exp_Insight_Type):
            sql = f"delete  dbo.t_mitigation_exp_insights where document_id = ?"

        elif (dictionary_type == Lookups().Mitigation_Int_Insight_Type):
            sql = f"delete t_mitigation_int_insights where document_id = ?"

        elif (dictionary_type == Lookups().Mitigation_Exp_INT_Insight_Type):
            sql = f"delete t_mitigation_exp_int_insights where document_id = ?"

        try:
            # Execute the SQL query
            cursor.execute(sql, document_id)
            self.dbConnection.commit()

        except Exception as exc:
            # Rollback the transaction if any error occurs
            self.dbConnection.rollback()
            print(f"Error: {str(exc)}")
            raise exc

    def save_key_word_hits(self, proximity_entity_list, company_id: int, document_id: int, document_name: str, reporting_year: int, dictionary_type: int, batch_id: int):

        # Delete existing records for the same document
        try:
            sql = 'delete t_key_word_hits where document_id = ? and dictionary_type = ?'
            cursor = self.dbConnection.cursor()
            cursor.execute(sql, document_id, dictionary_type)
            self.dbConnection.commit()
            # print("deleted previous search data for document:" + document_name +", dictionary type:" + str(dictionary_type))
        except Exception as exc:
            # Rollback the transaction if any error occurs
            self.dbConnection.rollback()
            print(f"Error Deleting Keyword hits for :"+document_name)
            print(f"Error: {str(exc)}")
            raise exc

        self.d_next_seed = 0

        proximity: ProximityEntity
        key_word_locations: KeyWordLocationsEntity

        total_records_added_to_db = 0
        for proximity in proximity_entity_list:

            esg_category_id = proximity.esg_category_id
            impact_category_id = proximity.impact_category_id
            exposure_path_id = proximity.exposure_path_id
            internalization_id = proximity.internalization_id
            dictionary_id = proximity.dictionary_id

            for key_word_locations in proximity.key_word_bunch:
                # batch_id = self.get_current_batch_id()
                key_word = key_word_locations.key_word
                locations = key_word_locations.locations
                frequency = key_word_locations.frequency
                self.insert_key_word_hits_to_db(company_id=company_id, document_id=document_id, document_name=document_name,
                                                reporting_year=reporting_year, dictionary_id=dictionary_id,
                                                key_word=key_word, locations=locations, frequency=frequency, dictionary_type=dictionary_type,
                                                exposure_path_id=exposure_path_id, internalization_id=internalization_id, impact_category_id=impact_category_id, esg_category_id=esg_category_id, batch_id=batch_id)
                total_records_added_to_db = total_records_added_to_db + 1
            # Commit current batch
            self.dbConnection.commit()
        self.log_generator.log_details(
            "Total keyword location lists Added to the Database:" + str(total_records_added_to_db))
        self.log_generator.log_details(
            '################################################################################################')

        # print("Total keyword location lists Added to the Database:" +
        #       str(total_records_added_to_db))
        # print('################################################################################################')

    def update_insights_generated_from_keyword_hits_batch(self, dictionary_type=0, dictionary_id=0, document_id=0):
        # Create a cursor object to execute SQL queries
        cursor = self.dbConnection.cursor()

        # sql = f"update t_key_word_hits set \
        #         insights_generated = 1 ,modify_dt = CURRENT_TIMESTAMP ,modify_by = N'Mohan Hanumantha'\
        #         where batch_id ={batch_id} and insights_generated = 0 and dictionary_type ={dictionary_type} and dictionary_id ={dictionary_id} and document_id ={document_id}"

        if (dictionary_type == Lookups().Exposure_Pathway_Dictionary_Type):
            sql = f"update t_document set exp_insights_generated_ind = 1 \
                    ,modify_dt = CURRENT_TIMESTAMP ,modify_by = N'Mohan Hanumantha'\
                    where document_id ={document_id}"
        elif (dictionary_type == Lookups().Internalization_Dictionary_Type):
            sql = f"update t_document set int_insights_generated_ind = 1 \
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

    def update_validation_keywords_generated_status(self, document_list, dictionary_type, status):
        if (dictionary_type == Lookups().Exposure_Pathway_Dictionary_Type):
            sql = f"UPDATE t_document set exp_validation_completed_ind = ? where document_id = ?"
        elif (dictionary_type == Lookups().Internalization_Dictionary_Type):
            sql = f"UPDATE t_document set int_validation_completed_ind = ? where document_id = ?"
        elif (dictionary_type == Lookups().Mitigation_Dictionary_Type):
            sql = f"UPDATE t_document set mit_validation_completed_ind = ? where document_id = ?"

        for document in document_list:
            # print('Document ID:'+str(document.document_id) +', Status:'+str(status))
            # print(sql)
            try:
                cursor = self.dbConnection.cursor()
                cursor.execute(sql, status, document.document_id)

            except Exception as exc:
                self.dbConnection.rollback()
                print(f"Error: {str(exc)}")
                raise exc
        self.dbConnection.commit()
        cursor.close()

    def update_validation_completed_status(self):
        exp_sql = f"UPDATE t_document set \
                        exp_validation_completed_ind = 1,,modify_dt = CURRENT_TIMESTAMP ,\
                  where \
                        exp_validation_completed_ind = 2 and exp_pathway_keyword_search_completed_ind = 0"

        int_sql = f"UPDATE t_document set \
                        int_validation_completed_ind =1,modify_dt = CURRENT_TIMESTAMP ,\
                    where \
                        int_validation_completed_ind = 2 and internalization_keyword_search_completed_ind = 0"

        mit_sql = f"UPDATE t_document set \
                        mit_validation_completed_ind = 1,modify_dt = CURRENT_TIMESTAMP ,\
                    where \
                        mit_validation_completed_ind = 2 and mitigation_search_completed_ind = 0"
        try:
            cursor = self.dbConnection.cursor()
            cursor.execute(exp_sql)
            cursor.execute(int_sql)
            cursor.execute(mit_sql)

        except Exception as exc:
            self.dbConnection.rollback()
            print(f"Error: {str(exc)}")
            raise exc
        self.dbConnection.commit()
        cursor.close()

    def update_validation_failed_status(self, document_id, dictionary_type):

        exp_sql = f"UPDATE t_document set exp_validation_completed_ind = 0 where document_id ={document_id}"
        int_sql = f"UPDATE t_document set int_validation_completed_ind = 0 where document_id ={document_id}"
        mit_sql = f"UPDATE t_document set  mit_validation_completed_ind = 0 where document_id ={document_id}"

        try:
            cursor = self.dbConnection.cursor()

            if (dictionary_type == Lookups().Exposure_Pathway_Dictionary_Type):
                cursor.execute(exp_sql)
            if (dictionary_type == Lookups().Internalization_Dictionary_Type):
                cursor.execute(int_sql)
            if (dictionary_type == Lookups().Internalization_Dictionary_Type):
                cursor.execute(mit_sql)
        except Exception as exc:
            self.dbConnection.rollback()
            print(f"Error: {str(exc)}")
            raise exc

        self.dbConnection.commit()
        cursor.close()


# EXPOSURE PATHWAY

    def get_exp_dictionary_term_list(self):

        exp_dict_terms_list = []

        # sql = "select d.dictionary_id,d.keywords,d.exposure_path_id from t_exposure_pathway_dictionary d where d.dictionary_id = 1001"
        sql = "select esg.esg_category_id, imp.impact_category_id, exp.exposure_path_id, d.dictionary_id,d.keywords \
              from t_exposure_pathway_dictionary d INNER JOIN  t_exposure_pathway exp on d.exposure_path_id = exp.exposure_path_id\
                                INNER JOIN  t_impact_category imp on imp.impact_category_id = exp.impact_category_id\
                                INNER JOIN t_esg_category esg on esg.esg_category_id = imp.esg_category_id"
        #  where dictionary_id = 1005"
        # DEBUG COMMENT LINE ABOVE

        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row in rows:
                exp_dict_terms_list.append(DictionaryEntity(
                    esg_category_id=row.esg_category_id, impact_category_id=row.impact_category_id, exposure_path_id=row.exposure_path_id,
                    dictionary_id=row.dictionary_id, keywords=row.keywords)
                )
            cursor.close()

        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

        return exp_dict_terms_list

    def get_exp_pathway_document_list(self, validation_mode: bool):
        document_list = []
        if (validation_mode):
            validation_completed_ind = 0
        else:
            validation_completed_ind = 1

        try:
            cursor = self.dbConnection.cursor()

            sql = "select doc.document_id, comp.company_id, doc.document_name, doc.company_name, doc.year, doc.batch_id \
                            from dbo.t_document doc, t_sec_company comp \
                            where \
                            doc.exp_pathway_keyword_search_completed_ind in(0,2) and doc.company_name = comp.conformed_name and doc.exp_validation_completed_ind=? order by doc.document_id"

            cursor.execute(sql, validation_completed_ind)

            rows = cursor.fetchall()
            for row in rows:
                document_entity = DocumentEntity()
                document_entity.document_id = row.document_id
                document_entity.document_name = row.document_name
                document_entity.company_name = row.company_name
                document_entity.company_id = row.company_id
                document_entity.year = row.year
                document_entity.batch_id = row.batch_id
                document_list.append(document_entity)
            cursor.close()
        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

        return document_list

    def update_exp_pathway_keyword_search_completed_ind(self, document_id, search_failed=False, validation_failed=False):
        # Create a cursor object to execute SQL queries
        if (validation_failed):
            self.update_validation_failed_status(
                document_id=document_id, dictionary_type=Lookups().Exposure_Pathway_Dictionary_Type)
        if (not search_failed):
            completed_ind = 1
        else:
            completed_ind = 2
        cursor = self.dbConnection.cursor()

        sql = f"update t_document set exp_pathway_keyword_search_completed_ind ={completed_ind} \
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

# INTERNALIZAITON
    def get_int_dictionary_term_list(self):

        int_dict_terms_list = []

        sql = "select d.dictionary_id,keywords,internalization_id from t_internalization_dictionary d"
        # where d.dictionary_id in(1004,1012)"
        # DEBUG COMMENT LINE ABOVE
        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row in rows:
                int_dict_terms_list.append(DictionaryEntity(
                    dictionary_id=row.dictionary_id, keywords=row.keywords, internalization_id=row.internalization_id))
            cursor.close()

        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

        return int_dict_terms_list

    def get_internalization_document_list(self, validation_mode: bool):
        document_list = []
        if (validation_mode):
            validation_completed_ind = 0
        else:
            validation_completed_ind = 1

        try:
            cursor = self.dbConnection.cursor()
            sql = "select doc.document_id, comp.company_id, doc.document_name, doc.company_name, doc.year, doc.batch_id \
                            from dbo.t_document doc, t_sec_company comp \
                            where \
                            doc.internalization_keyword_search_completed_ind in(0,2) and doc.company_name = comp.conformed_name and doc.int_validation_completed_ind =?  order by doc.document_id"

            cursor.execute(sql, validation_completed_ind)
            rows = cursor.fetchall()
            for row in rows:
                document_entity = DocumentEntity()
                document_entity.document_id = row.document_id
                document_entity.document_name = row.document_name
                document_entity.company_name = row.company_name
                document_entity.company_id = row.company_id
                document_entity.year = row.year
                document_entity.batch_id = row.batch_id
                document_list.append(document_entity)
            cursor.close()
        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

        return document_list

    def update_internalization_keyword_search_completed_ind(self, document_id, search_failed=False, validation_failed=False):

        if (validation_failed):
            self.update_validation_failed_status(
                document_id=document_id, dictionary_type=Lookups().Internalization_Dictionary_Type)

        if (not search_failed):
            completed_ind = 1
        else:
            completed_ind = 2
        # Create a cursor object to execute SQL queries
        cursor = self.dbConnection.cursor()

        sql = f"update t_document set internalization_keyword_search_completed_ind = {completed_ind} \
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


# MITIGATION

    def get_mitigation_dictionary_term_list(self):

        mitigation_dict_terms_list = []

        sql = "select dictionary_id,keywords from t_mitigation"

        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row in rows:
                mitigation_dict_terms_list.append(DictionaryEntity(
                    dictionary_id=row.dictionary_id, keywords=row.keywords))
            cursor.close()

        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

        return mitigation_dict_terms_list

        pass

    def get_mitigation_document_list(self, validation_mode: bool):
        document_list = []
        if (validation_mode):
            validation_completed_ind = 0
        else:
            validation_completed_ind = 1

        try:
            cursor = self.dbConnection.cursor()
            sql = "select doc.document_id, comp.company_id, doc.document_name, doc.company_name, doc.year, doc.batch_id \
                            from dbo.t_document doc, t_sec_company comp \
                            where \
                            doc.mitigation_search_completed_ind in(0,2) and doc.company_name = comp.conformed_name and doc.mit_validation_completed_ind=? order by document_id"

            cursor.execute(sql, validation_completed_ind)

            rows = cursor.fetchall()
            for row in rows:
                document_entity = DocumentEntity()
                document_entity.document_id = row.document_id
                document_entity.document_name = row.document_name
                document_entity.company_name = row.company_name
                document_entity.company_id = row.company_id
                document_entity.year = row.year
                document_entity.batch_id = row.batch_id

                document_list.append(document_entity)
            cursor.close()
        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

        return document_list

    def update_mitigation_keyword_search_completed_ind(self, document_id, search_failed=False, validation_failed=False):

        if (validation_failed):
            self.update_validation_failed_status(
                document_id=document_id, dictionary_type=Lookups().Mitigation_Dictionary_Type)

        if (not search_failed):
            completed_ind = 1
        else:
            completed_ind = 2

        # Create a cursor object to execute SQL queries
        cursor = self.dbConnection.cursor()

        sql = f"update t_document set mitigation_search_completed_ind = {completed_ind} \
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

# TRIANGULATION

    # COMMON

    def update_triangulation_insights_generated_batch(self, dictionary_type, document_id):

        cursor = self.dbConnection.cursor()

        # Create a cursor object to execute SQL queries
        if (dictionary_type == Lookups().Mitigation_Exp_Insight_Type):
            sql = f"update t_document set mitigation_exp_insights_generated = 1 \
                    ,modify_dt = CURRENT_TIMESTAMP ,modify_by = N'Mohan Hanumantha'\
                    where document_id ={document_id}"
        elif (dictionary_type == Lookups().Mitigation_Int_Insight_Type):
            sql = f"update t_document set mitigation_int_insights_generated = 1 \
                    ,modify_dt = CURRENT_TIMESTAMP ,modify_by = N'Mohan Hanumantha'\
                    where document_id ={document_id}"
        elif (dictionary_type == Lookups().Exp_Int_Insight_Type):
            sql = f"update t_document set int_exp_insights_generated = 1 \
            ,modify_dt = CURRENT_TIMESTAMP ,modify_by = N'Mohan Hanumantha'\
            where document_id ={document_id}"
        elif (dictionary_type == Lookups().Mitigation_Exp_INT_Insight_Type):
            sql = f"update t_document set mitigation_int_exp_insights_generated = 1 \
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

    # EXP MITIGATION
    def get_exp_mitigation_document_list(self):
        document_list = []
        try:
            cursor = self.dbConnection.cursor()
            cursor.execute("select doc.document_id, comp.company_id, doc.document_name, doc.company_name, doc.year \
                            from dbo.t_document doc, t_sec_company comp \
                            where \
                            doc.mitigation_exp_insights_generated = 0 and doc.company_name = comp.conformed_name\
                            and doc.exp_insights_generated_ind = 1 and doc.mitigation_search_completed_ind = 1\
                           ")
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

    def get_exp_mitigation_lists(self, document_id):

        mitigation_keyword_list = []
        sql = 'select document_id, key_word_hit_id, key_word,locations from t_key_word_hits where  dictionary_type = 1002 and document_id = ?  order by key_word_hit_id'

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

        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

        exp_keyword_list = []
        sql = 'select document_id, key_word_hit_id, key_word,locations,exposure_path_id from t_key_word_hits where dictionary_type = 1000 and document_id = ? order by key_word_hit_id'
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
                keyword_loc_entity.exposure_path_id = row.exposure_path_id
                exp_keyword_list.append(keyword_loc_entity)

            cursor.close()

            # print("Record inserted successfully!")

        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

        exp_insight_list = []
        sql = 'select key_word_hit_id1, key_word_hit_id2, key_word1, key_word2,exposure_path_id from t_exposure_pathway_insights where document_id = ? and score_normalized > ?'
        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor()
            cursor.execute(sql, document_id, INSIGHT_SCORE_THRESHOLD)
            rows = cursor.fetchall()
            for row in rows:

                insight_entity = Insight()
                insight_entity.keyword_hit_id1 = row.key_word_hit_id1
                insight_entity.keyword_hit_id2 = row.key_word_hit_id2
                insight_entity.keyword1 = row.key_word1
                insight_entity.keyword2 = row.key_word2
                insight_entity.exposure_path_id = row.exposure_path_id
                exp_insight_list.append(insight_entity)

            cursor.close()

            # print("Record inserted successfully!")

        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

        return mitigation_keyword_list, exp_keyword_list, exp_insight_list

    # INT MITIGATION
    def get_int_mitigation_document_list(self):
        document_list = []
        try:
            cursor = self.dbConnection.cursor()
            cursor.execute("select doc.document_id, comp.company_id, doc.document_name, doc.company_name, doc.year \
                            from dbo.t_document doc, t_sec_company comp \
                            where \
                            doc.mitigation_int_insights_generated = 0 and doc.company_name = comp.conformed_name\
                           and doc.int_insights_generated_ind = 1 and doc.mitigation_search_completed_ind = 1\
                           ")
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

    def get_int_mitigation_lists(self, document_id):

        mitigation_keyword_list = []
        sql = 'select document_id, key_word_hit_id, key_word,locations from t_key_word_hits where  dictionary_type = 1002 and document_id = ?  order by key_word_hit_id'

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

        int_keyword_list = []
        sql = 'select document_id, key_word_hit_id, key_word,locations,internalization_id from t_key_word_hits where dictionary_type = 1001 and document_id = ? order by key_word_hit_id'
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
                keyword_loc_entity.intenalization_id = row.internalization_id
                int_keyword_list.append(keyword_loc_entity)

            cursor.close()

            # print("Record inserted successfully!")

        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

        int_insight_list = []
        sql = 'select key_word_hit_id1, key_word_hit_id2, key_word1, key_word2,internalization_id from t_internalization_insights where document_id = ? and score_normalized > ?'
        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor()
            cursor.execute(sql, document_id, INSIGHT_SCORE_THRESHOLD)
            rows = cursor.fetchall()
            for row in rows:

                insight_entity = Insight()
                insight_entity.keyword_hit_id1 = row.key_word_hit_id1
                insight_entity.keyword_hit_id2 = row.key_word_hit_id2
                insight_entity.keyword1 = row.key_word1
                insight_entity.keyword2 = row.key_word2
                insight_entity.internalization_id = row.internalization_id

                int_insight_list.append(insight_entity)

            cursor.close()

            # print("Record inserted successfully!")

        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

        return mitigation_keyword_list, int_keyword_list, int_insight_list

    # EXP INT
    def get_exp_int_document_list(self):
        document_list = []
        try:
            cursor = self.dbConnection.cursor()
            cursor.execute("select doc.document_id, comp.company_id, doc.document_name, doc.company_name, doc.year \
                            from dbo.t_document doc, t_sec_company comp \
                            where \
                            doc.int_exp_insights_generated = 0 and doc.company_name = comp.conformed_name\
                            and doc.exp_insights_generated_ind = 1 and doc.int_insights_generated_ind = 1\
                           ")
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

    def get_exp_int_lists(self, document_id):

        exp_insight_location_list = []
        # sql = 'select document_id, key_word_hit_id, key_word,locations from t_key_word_hits where dictionary_type = 1000 and document_id = ?'

        sql = f"select exp.key_word_hit_id1, exp.key_word_hit_id2, exp.key_word1, exp.key_word2, hits.locations locationlist1, hits2.locations locationlist2 , exp.exposure_path_id\
                 from t_exposure_pathway_insights exp inner join  t_key_word_hits hits on hits.key_word_hit_id = exp.key_word_hit_id1 \
                                             inner join   t_key_word_hits hits2 on hits2.key_word_hit_id = exp.key_word_hit_id2 \
                where exp.document_id = ? and score_normalized > ?"

        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor()
            cursor.execute(sql, document_id, INSIGHT_SCORE_THRESHOLD)
            rows = cursor.fetchall()
            for row in rows:
                insight_entity = Insight()
                insight_entity.keyword_hit_id1 = row.key_word_hit_id1
                insight_entity.keyword_hit_id2 = row.key_word_hit_id2
                insight_entity.keyword1 = row.key_word1
                insight_entity.keyword2 = row.key_word2
                insight_entity.locations1 = row.locationlist1
                insight_entity.locations2 = row.locationlist2
                insight_entity.exposure_path_id = row.exposure_path_id
                exp_insight_location_list.append(insight_entity)
            cursor.close()

        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

        int_insight_location_list = []

        sql = f"select int.key_word_hit_id1, int.key_word_hit_id2, int.key_word1, int.key_word2, hits.locations locationlist1, hits2.locations locationlist2, int.internalization_id\
                from t_internalization_insights int inner join  t_key_word_hits hits on hits.key_word_hit_id = int.key_word_hit_id1 \
                                     inner join   t_key_word_hits hits2 on hits2.key_word_hit_id = int.key_word_hit_id2      \
                where int.document_id = ? and score_normalized > ? "

        try:
            # Execute the SQL query
            cursor = self.dbConnection.cursor()
            cursor.execute(sql, document_id, INSIGHT_SCORE_THRESHOLD)
            rows = cursor.fetchall()
            for row in rows:
                insight_entity = Insight()
                insight_entity.keyword_hit_id1 = row.key_word_hit_id1
                insight_entity.keyword_hit_id2 = row.key_word_hit_id2
                insight_entity.keyword1 = row.key_word1
                insight_entity.keyword2 = row.key_word2
                insight_entity.locations1 = row.locationlist1
                insight_entity.locations2 = row.locationlist2
                insight_entity.internalization_id = row.internalization_id
                int_insight_location_list.append(insight_entity)
            cursor.close()

        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

        return exp_insight_location_list, int_insight_location_list

    def save_Exp_Int_Insights(self, insightList, dictionary_type):
        exp_int_insight_entity: ExpIntInsight
        self.d_next_seed = 0

        total_records_added_to_db = 0
        for exp_int_insight_entity in insightList:
            exp_keyword_hit_id1 = exp_int_insight_entity.exp_keyword_hit_id1
            exp_keyword1 = exp_int_insight_entity.exp_keyword1
            exp_keyword_hit_id2 = exp_int_insight_entity.exp_keyword_hit_id2
            exp_keyword2 = exp_int_insight_entity.exp_keyword2
            int_key_word_hit_id1 = exp_int_insight_entity.int_key_word_hit_id1
            int_key_word1 = exp_int_insight_entity.int_key_word1
            int_key_word_hit_id2 = exp_int_insight_entity.int_key_word_hit_id2
            int_key_word2 = exp_int_insight_entity.int_key_word2
            factor1 = exp_int_insight_entity.factor1
            factor2 = exp_int_insight_entity.factor2
            score = exp_int_insight_entity.score
            document_name = exp_int_insight_entity.document_name
            document_id = exp_int_insight_entity.document_id
            exposure_path_id = exp_int_insight_entity.exposure_path_id
            internalization_id = exp_int_insight_entity.internalization_id
            year = exp_int_insight_entity.year

            # Create a cursor object to execute SQL queries
            cursor = self.dbConnection.cursor()
            # Construct the INSERT INTO statement

            sql = f"INSERT INTO dbo.t_exp_int_insights( \
                        document_id , document_name ,exp_keyword_hit_id1 ,exp_keyword1,exp_keyword_hit_id2 ,exp_keyword2 \
                        ,int_key_word_hit_id1,int_key_word1,int_key_word_hit_id2, int_key_word2 ,factor1 ,factor2 ,score, exposure_path_id, internalization_id\
                        ,added_dt,added_by ,modify_dt,modify_by,year\
                )\
                    VALUES\
                    ({document_id},N'{document_name}',{exp_keyword_hit_id1},N'{exp_keyword1}',{exp_keyword_hit_id2},N'{exp_keyword2}'\
                    ,{int_key_word_hit_id1},N'{int_key_word1}',{int_key_word_hit_id2},N'{int_key_word2}'\
                    , {factor1}, {factor2},{score},{exposure_path_id},{internalization_id}\
                    ,CURRENT_TIMESTAMP, N'Mohan Hanumantha',CURRENT_TIMESTAMP, N'Mohan Hanumantha',{year})"

            try:
                # Execute the SQL query
                cursor.execute(sql)
                total_records_added_to_db = total_records_added_to_db + 1
                if (total_records_added_to_db % 50 == 0):
                    self.dbConnection.commit()

            except Exception as exc:
                # Rollback the transaction if any error occurs
                self.dbConnection.rollback()
                print(f"Error: {str(exc)}")
                raise exc

            # if (total_records_added_to_db % 250 == 0):
            #     print("Insights added to the Database So far...:" +
            #           str(total_records_added_to_db))

        # Close the cursor and connection

        if (total_records_added_to_db > 0):
            self.dbConnection.commit()
            cursor.close()

        # self.dbConnection.commit()
        if (DB_LOGGING_ENABLED):
            self.log_generator.log_details(
                "Total Insights added to the Database:" + str(total_records_added_to_db))
            self.log_generator.log_details(
                '################################################################################################')

        # print("Total Insights added to the Database:" +
        #       str(total_records_added_to_db))

    # EXP INT MITIGATION
    def get_mitigation_exp_int_document_list(self):
        document_list = []
        try:
            cursor = self.dbConnection.cursor()
            cursor.execute("select doc.document_id, comp.company_id, doc.document_name, doc.company_name, doc.year \
                            from dbo.t_document doc, t_sec_company comp \
                            where \
                            doc.mitigation_int_exp_insights_generated = 0 and doc.company_name = comp.conformed_name\
                            and doc.exp_insights_generated_ind=1 and doc.int_insights_generated_ind=1 and doc.mitigation_search_completed_ind = 1\
                           ")
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

    def get_mitigation_exp_int_lists(self, document_id):

        mitigation_keyword_list = []
        sql = 'select document_id, key_word_hit_id, key_word,locations from t_key_word_hits where insights_generated = 0 and dictionary_type = 1002 and document_id = ?  order by key_word_hit_id'

        # sql = 'select document_id, key_word_hit_id, key_word,locations from t_key_word_hits where  insights_generated = 0 and \
        #         dictionary_type = 1002 and document_id = ?  and  dictionary_id = 1009 and key_word_hit_id = 1585'

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

        exp_int_insight_location_list = []
        # sql = 'select document_id, key_word_hit_id, key_word,locations from t_key_word_hits where dictionary_type = 1000 and document_id = ?'

        sql = f"SELECT expint.unique_key,expint.document_id, expint.document_name, expint.exp_keyword_hit_id1,expint.exp_keyword1,expint.exp_keyword_hit_id2,expint.exp_keyword2,\
                expint.int_key_word_hit_id1,expint.int_key_word1, int_key_word_hit_id2,expint.int_key_word2,expint.factor1,expint.factor2,expint.score,expint.exposure_path_id,expint.internalization_id,\
                exp1_hits.locations 'exp1_locations', exp2_hits.locations 'exp2_locations', int1_hits.locations 'int1_locations', int2_hits.locations 'int2_locations'\
               from t_exp_int_insights expint \
                      INNER JOIN t_key_word_hits exp1_hits on exp1_hits.key_word_hit_id = expint.exp_keyword_hit_id1\
                      INNER JOIN t_key_word_hits exp2_hits on exp2_hits.key_word_hit_id = expint.exp_keyword_hit_id2\
                      INNER JOIN  t_key_word_hits int1_hits on int1_hits.key_word_hit_id = expint.int_key_word_hit_id1\
                      INNER JOIN  t_key_word_hits int2_hits on int2_hits.key_word_hit_id = expint.int_key_word_hit_id2\
                where expint.document_id = ? and expint.score_normalized > {EXP_INT_MITIGATION_THRESHOLD}"

        # where expint.document_id = ? and expint.score_normalized > {EXP_INT_MITIGATION_THRESHOLD}"
        # and expint.unique_key = 2441"

        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor()
            cursor.execute(sql, document_id)
            rows = cursor.fetchall()
            for row in rows:
                insight_entity = MitigationExpIntInsight()
                insight_entity.document_id = row.document_id
                insight_entity.exp_keyword_hit_id1 = row.exp_keyword_hit_id1
                insight_entity.exp_keyword1 = row.exp_keyword1
                insight_entity.exp_keyword_hit_id2 = row.exp_keyword_hit_id2
                insight_entity.exp_keyword2 = row.exp_keyword2
                insight_entity.int_key_word_hit_id1 = row.int_key_word_hit_id1
                insight_entity.int_key_word1 = row.int_key_word1
                insight_entity.int_key_word_hit_id2 = row.int_key_word_hit_id2
                insight_entity.int_key_word2 = row.int_key_word2
                insight_entity.document_name = row.document_name
                insight_entity.document_id = document_id
                insight_entity.internalization_id = row.internalization_id
                insight_entity.exposure_path_id = row.exposure_path_id
                insight_entity.exp1_locations = row.exp1_locations
                insight_entity.exp2_locations = row.exp2_locations
                insight_entity.int1_locations = row.int1_locations
                insight_entity.int2_locations = row.int2_locations
                exp_int_insight_location_list.append(insight_entity)
            cursor.close()

        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

        return exp_int_insight_location_list, mitigation_keyword_list

    def save_Mitigation_Exp_Int_Insights(self, insightList, dictionary_type):
        mitigation_exp_int_insight_entity: MitigationExpIntInsight
        self.d_next_seed = 0

        total_records_added_to_db = 0
        for mitigation_exp_int_insight_entity in insightList:
            exp_keyword_hit_id1 = mitigation_exp_int_insight_entity.exp_keyword_hit_id1
            exp_keyword1 = mitigation_exp_int_insight_entity.exp_keyword1
            exp_keyword_hit_id2 = mitigation_exp_int_insight_entity.exp_keyword_hit_id2
            exp_keyword2 = mitigation_exp_int_insight_entity.exp_keyword2
            int_key_word_hit_id1 = mitigation_exp_int_insight_entity.int_key_word_hit_id1
            int_key_word1 = mitigation_exp_int_insight_entity.int_key_word1
            int_key_word_hit_id2 = mitigation_exp_int_insight_entity.int_key_word_hit_id2
            int_key_word2 = mitigation_exp_int_insight_entity.int_key_word2
            factor1 = mitigation_exp_int_insight_entity.factor1
            factor2 = mitigation_exp_int_insight_entity.factor2
            score = mitigation_exp_int_insight_entity.score
            document_name = mitigation_exp_int_insight_entity.document_name
            document_id = mitigation_exp_int_insight_entity.document_id
            exposure_path_id = mitigation_exp_int_insight_entity.exposure_path_id
            internalization_id = mitigation_exp_int_insight_entity.internalization_id
            mitigation_keyword_hit_id = mitigation_exp_int_insight_entity.mitigation_keyword_hit_id
            mitigation_keyword = mitigation_exp_int_insight_entity.mitigation_keyword
            year = mitigation_exp_int_insight_entity.year

            # Create a cursor object to execute SQL queries
            cursor = self.dbConnection.cursor()
            # Construct the INSERT INTO statement

            # int_unique_key = self.get_next_surrogate_key(
            #     Lookups().Mitigation_Exp_INT_Insight_Type)
            sql = f"INSERT INTO dbo.t_mitigation_exp_int_insights( \
                        document_id , document_name ,exp_keyword_hit_id1 ,exp_keyword1,exp_keyword_hit_id2 ,exp_keyword2 \
                        ,int_key_word_hit_id1,int_key_word1,int_key_word_hit_id2, int_key_word2 ,factor1 ,factor2 ,score, exposure_path_id, internalization_id\
                        ,mitigation_keyword_hit_id,mitigation_keyword\
                        ,added_dt,added_by ,modify_dt,modify_by,year\
                )\
                    VALUES\
                    ({document_id},N'{document_name}',{exp_keyword_hit_id1},N'{exp_keyword1}',{exp_keyword_hit_id2},N'{exp_keyword2}'\
                    ,{int_key_word_hit_id1},N'{int_key_word1}',{int_key_word_hit_id2},N'{int_key_word2}'\
                    , {factor1}, {factor2},{score},{exposure_path_id},{internalization_id}\
                    ,{mitigation_keyword_hit_id},N'{mitigation_keyword}'\
                    ,CURRENT_TIMESTAMP, N'Mohan Hanumantha',CURRENT_TIMESTAMP, N'Mohan Hanumantha', {year})"

            try:
                # Execute the SQL query
                cursor.execute(sql)
                total_records_added_to_db = total_records_added_to_db + 1
                if (total_records_added_to_db % 50 == 0):
                    self.dbConnection.commit()

            except Exception as exc:
                # Rollback the transaction if any error occurs
                self.dbConnection.rollback()
                print(f"Error: {str(exc)}")
                raise exc

            # if (total_records_added_to_db % 250 == 0):
            #     print("Insights added to the Database So far...:" +
            #           str(total_records_added_to_db))

        # Close the cursor and connection
        if (total_records_added_to_db > 0):
            self.dbConnection.commit()
            cursor.close()

        # self.dbConnection.commit()
        if (DB_LOGGING_ENABLED):
            self.log_generator.log_details(
                "Total Insights added to the Database:" + str(total_records_added_to_db))
            self.log_generator.log_details(
                '################################################################################################')

        # print("Total Insights added to the Database:" +
        #       str(total_records_added_to_db))

    # Build SECTOR aggregate tables

    def get_sector_list(self):

        sector_list = []

        sql = 'select l.data_lookups_id sector_id, l.data_lookups_description  sector from t_data_lookups l where data_lookups_group_id = 5 order by l.data_lookups_description'

        try:
            # Execute the SQL query
            cursor = self.dbConnection.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row in rows:
                sector_list.append(row.sector)

        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

        return sector_list

    def get_year_list(self):
        year_list = []

        sql = 'select distinct year from t_document order by year desc'

        try:
            # Execute the SQL query
            cursor = self.dbConnection.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row in rows:
                year_list.append(row.year)

        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

        return year_list

    def get_sector_id_year_list(self):
        sector_year_list = []

        sector_list = []

        sql = 'select l.data_lookups_id sector_id from t_data_lookups l where data_lookups_group_id = 5 order by l.data_lookups_description'

        try:
            # Execute the SQL query
            cursor = self.dbConnection.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row in rows:
                sector_list.append(row.sector_id)
            cursor.close()

        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

        year_list = self.get_year_list()

        for sector_id in sector_list:
            for year in year_list:
                sector_year_list.append(SectorYearDBEntity(
                    SectorId=sector_id, Year=year))
        return sector_year_list

    def get_company_list(self):
        company_list = []

        sql = 'select distinct company_name from t_sec_company_sector_map order by company_name'

        try:
            # Execute the SQL query
            cursor = self.dbConnection.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row in rows:
                company_list.append(row.company_name)

        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

        return company_list

    def get_doc_type_list(self):
        doc_type_list = []

        sql = 'select data_lookups_description doc_type from t_data_lookups where data_lookups_group_id = 1'

        try:
            # Execute the SQL query
            cursor = self.dbConnection.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row in rows:
                doc_type_list.append(row.doc_type)

        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

        return doc_type_list

    def update_sector_stats(self, sector, year, generate_exp_sector_insights: bool, generate_int_sector_insights: bool, generate_exp_mit_sector_insights: bool, generate_exp_int_mit_sector_insights: bool, update_all: bool):
        sector_year_list = []
        if (update_all):
            sector_year_list = self.get_sector_id_year_list()
        else:

            # print('Sector Selected: '+sector)
            sector_id_sql = 'select lookups.data_lookups_id from t_data_lookups lookups where data_lookups_description = ?'
            cursor = self.dbConnection.cursor()
            cursor.execute(sector_id_sql, sector)
            sector_id = cursor.fetchone()[0]
            sector_year_list.append(SectorYearDBEntity(
                SectorId=sector_id, Year=year))

        # print('Sector ID: '+str(sector_id))
        # print('Year:'+str(year))

        sector_year: SectorYearDBEntity
        for sector_year in sector_year_list:
            if (generate_exp_sector_insights):
                self.update_sector_exposure_stats(
                    sector_year.SectorId, sector_year.Year)
            if (generate_int_sector_insights):
                self.update_sector_exposure_internalization_stats(
                    sector_year.SectorId, sector_year.Year)
            if (generate_exp_int_mit_sector_insights):
                self.update_sector_exposure_int_mitigation_stats(
                    sector_year.SectorId, sector_year.Year)
            if (generate_exp_mit_sector_insights):
                self.update_sector_exposure__mitigation_stats(
                    sector_year.SectorId, sector_year.Year)

    def update_sector_exposure_stats(self, sector_id, year):
        print('Updating Exposure STATS for Sector:' +
              str(sector_id)+', Year:'+str(year))

        # sector_id_sql = 'select lookups.data_lookups_id from t_data_lookups lookups where data_lookups_description = ?'
        # cursor = self.dbConnection.cursor()
        # cursor.execute(sector_id_sql, sector)
        # sector_id = cursor.fetchone()[0]

        # Exposure Pathway Sector STATS
        sql_update = 'update t_exposure_pathway_insights\
                      set score_normalized_sector = (score * 100)/(select max(score) from t_exposure_pathway_insights where sector_id = ? and year =?)\
                      where sector_id = ? and year = ?'
        cursor = self.dbConnection.cursor()
        cursor.execute(sql_update, sector_id, year, sector_id, year)
        self.dbConnection.commit()
        cursor.close()

        sql_delete = 'delete from t_sector_exp_insights where sector_id =? and year = ?'
        cursor = self.dbConnection.cursor()
        cursor.execute(sql_delete, sector_id, year)
        self.dbConnection.commit()
        cursor.close()

        sql_insert = 'INSERT into t_sector_exp_insights(sector_id,year,esg_category_name,exposure_path_name,cluster_count_all,cluster_count,score,score_normalized,added_dt,added_by,modify_dt,modify_by)\
                SELECT \
                    insights.sector_id,insights.year,  esg.esg_category_name ESG_Category,  exp.exposure_path_name Exposure_Pathway,\
                    count(*) Pathways, NULL, AVG(insights.score_normalized_sector) Score,  NULL, CURRENT_TIMESTAMP, ?,CURRENT_TIMESTAMP, ?\
                FROM t_exposure_pathway_insights insights \
                        inner join t_exposure_pathway exp on exp.exposure_path_id = insights.exposure_path_id \
                        inner join t_impact_category imp on exp.impact_category_id = imp.impact_category_id\
                        inner join t_esg_category esg on imp.esg_category_id = esg.esg_category_id\
                WHERE insights.sector_id = ? and insights.year = ?\
                GROUP BY insights.sector_id,insights.year,  esg.esg_category_name ,  exp.exposure_path_name'
        cursor = self.dbConnection.cursor()
        cursor.execute(sql_insert, 'MOHAN HANUMANTHA',
                       'MOHAN HANUMANTHA', sector_id, year)
        self.dbConnection.commit()
        cursor.close()

        sql_update_cluster = 'update t_sector_exp_insights set cluster_count = cluster_count_all/(select count(document_id) from t_document doc inner join t_sec_company_sector_map map on doc.company_name = map.company_name where map.sector_id = ? and  doc.year = ?)\
                        where  sector_id = ? and year = ?'

        cursor = self.dbConnection.cursor()
        cursor.execute(sql_update_cluster, sector_id, year, sector_id, year)
        self.dbConnection.commit()
        cursor.close()

        sql_update_normalize_score = 'update t_sector_exp_insights\
                                   set score_normalized = (score * 100)/(select max(score) from t_sector_exp_insights where sector_id = ? and year =?)\
                                   where sector_id = ? and year = ?'
        cursor = self.dbConnection.cursor()
        cursor.execute(sql_update_normalize_score,
                       sector_id, year, sector_id, year)
        self.dbConnection.commit()
        cursor.close()

    def update_sector_exposure_internalization_stats(self, sector_id, year):
        print('Updating Internalization STATS for Sector:' +
              str(sector_id)+', Year:'+str(year))

        # sector_id_sql = 'select lookups.data_lookups_id from t_data_lookups lookups where data_lookups_description = ?'
        # cursor = self.dbConnection.cursor()
        # cursor.execute(sector_id_sql, sector)
        # sector_id = cursor.fetchone()[0]

        # Exposure Internalization Pathway Sector STATS
        sql_update = 'update t_exp_int_insights\
                      set score_normalized_sector = (score * 100)/(select max(score) from t_exp_int_insights where sector_id = ? and year =?)\
                      where sector_id = ? and year = ?'
        cursor = self.dbConnection.cursor()
        cursor.execute(sql_update, sector_id, year, sector_id, year)
        self.dbConnection.commit()
        cursor.close()

        sql_delete = 'delete from t_sector_exp_int_insights where sector_id =? and year = ?'
        cursor = self.dbConnection.cursor()
        cursor.execute(sql_delete, sector_id, year)
        self.dbConnection.commit()
        cursor.close()

        sql_insert = 'INSERT into t_sector_exp_int_insights(sector_id,year,esg_category_name,exposure_path_name,internalization_name,cluster_count_all,score,score_normalized,added_dt,added_by,modify_dt,modify_by)\
                    SELECT\
                            insights.sector_id,insights.year,  esg.esg_category_name ESG_Category,  exp.exposure_path_name Exposure_Pathway,int.internalization_name,\
                            count(*) Pathways, AVG(insights.score_normalized_sector) Score , NULL, CURRENT_TIMESTAMP, ?,CURRENT_TIMESTAMP, ?\
                FROM t_exp_int_insights insights \
                        inner join t_exposure_pathway exp on exp.exposure_path_id = insights.exposure_path_id\
                        inner join t_internalization int on int.internalization_id = insights.internalization_id\
                        inner join t_impact_category imp on exp.impact_category_id = imp.impact_category_id\
                        inner join t_esg_category esg on imp.esg_category_id = esg.esg_category_id\
                WHERE insights.sector_id = ? and insights.year = ?\
                GROUP BY insights.sector_id,insights.year,  esg.esg_category_name ,  exp.exposure_path_name,int.internalization_name'
        cursor = self.dbConnection.cursor()
        cursor.execute(sql_insert, 'MOHAN HANUMANTHA',
                       'MOHAN HANUMANTHA', sector_id, year)
        self.dbConnection.commit()
        cursor.close()

        # Update Cluster Count
        # print('updating cluster count')
        sql_update_cluster = 'update t_sector_exp_int_insights set cluster_count = cluster_count_all/(select count(document_id) from t_document doc inner join t_sec_company_sector_map map on doc.company_name = map.company_name where map.sector_id = ? and  doc.year = ?)\
                        where  sector_id = ? and year = ?'

        cursor = self.dbConnection.cursor()
        cursor.execute(sql_update_cluster, sector_id, year, sector_id, year)
        self.dbConnection.commit()
        cursor.close()

        # Normalize Score
        sql_update_normalize_score = 'update t_sector_exp_int_insights\
                                   set score_normalized = (score * 100)/(select max(score) from t_sector_exp_int_insights where sector_id = ? and year =?)\
                                   where sector_id = ? and year = ?'
        cursor = self.dbConnection.cursor()
        cursor.execute(sql_update_normalize_score,
                       sector_id, year, sector_id, year)
        self.dbConnection.commit()
        cursor.close()

    def update_sector_exposure_int_mitigation_stats(self, sector_id, year):
        print('Updating Exposure->Internalization->Mitigation STATS for Sector:' +
              str(sector_id)+', Year:'+str(year))

        # Exposure Internalization Pathway Sector STATS
        sql_update = 'update t_mitigation_exp_int_insights\
                      set score_normalized_sector = (score * 100)/(select max(score) from t_mitigation_exp_int_insights where sector_id = ? and year =?)\
                      where sector_id = ? and year = ?'

        cursor = self.dbConnection.cursor()
        cursor.execute(sql_update, sector_id, year, sector_id, year)
        self.dbConnection.commit()
        cursor.close()

        sql_delete = 'delete from t_sector_exp_int_mitigation_insights where sector_id =? and year = ?'
        cursor = self.dbConnection.cursor()
        cursor.execute(sql_delete, sector_id, year)
        self.dbConnection.commit()
        cursor.close()

        sql_insert = 'INSERT into t_sector_exp_int_mitigation_insights(sector_id,year,esg_category_name,exposure_path_name,internalization_name,mitigation_class,mitigation_sub_class,cluster_count_all,score,score_normalized,added_dt,added_by,modify_dt,modify_by)\
                      SELECT   insights.sector_id,insights.year Year,esg.esg_category_name ESG_Category,  exp.exposure_path_name Exposure_Pathway,\
                            int.internalization_name Internalization, mit.class_name,mit.sub_class_name, count(*) Pathways, AVG(insights.score_normalized_sector) Score, NULL, CURRENT_TIMESTAMP, ?,CURRENT_TIMESTAMP, ?\
                    FROM t_mitigation_exp_int_insights insights\
                        INNER JOIN t_exposure_pathway exp on exp.exposure_path_id = insights.exposure_path_id\
                        INNER JOIN t_internalization int on int.internalization_id = insights.internalization_id  and int.exposure_path_id = insights.exposure_path_id\
                        inner join t_impact_category imp on exp.impact_category_id = imp.impact_category_id\
                        inner join t_esg_category esg on imp.esg_category_id = esg.esg_category_id\
                        INNER JOIN t_key_word_hits hits on insights.mitigation_keyword_hit_id = hits.key_word_hit_id\
                        INNER JOIN t_mitigation mit on hits.dictionary_id = mit.dictionary_id\
                WHERE insights.sector_id = ? and insights.year = ?\
                GROUP by insights.sector_id,  insights.year,  esg.esg_category_name, exp.exposure_path_name,int.internalization_name, mit.class_name,mit.sub_class_name'
        cursor = self.dbConnection.cursor()
        cursor.execute(sql_insert, 'MOHAN HANUMANTHA',
                       'MOHAN HANUMANTHA', sector_id, year)
        self.dbConnection.commit()
        cursor.close()

        # Update Cluster Count
        # print('updating cluster count')
        sql_update_cluster = 'update t_sector_exp_int_mitigation_insights set cluster_count = cluster_count_all/(select count(document_id) from t_document doc inner join t_sec_company_sector_map map on doc.company_name = map.company_name where map.sector_id = ? and  doc.year = ?)\
                        where  sector_id = ? and year = ?'

        cursor = self.dbConnection.cursor()
        cursor.execute(sql_update_cluster, sector_id, year, sector_id, year)
        self.dbConnection.commit()
        cursor.close()

        # Normalize Score
        sql_update_normalize_score = 'update t_sector_exp_int_mitigation_insights\
                                   set score_normalized = (score * 100)/(select max(score) from t_sector_exp_int_mitigation_insights where sector_id = ? and year =?)\
                                   where sector_id = ? and year = ?'
        cursor = self.dbConnection.cursor()
        cursor.execute(sql_update_normalize_score,
                       sector_id, year, sector_id, year)
        self.dbConnection.commit()
        cursor.close()

    def update_sector_exposure__mitigation_stats(self, sector_id, year):
        print('Updating Exposure Mitigation STATS for Sector:' +
              str(sector_id)+', Year:'+str(year))

        # Exposure Internalization Pathway Sector STATS
        sql_update = 'update t_mitigation_exp_insights\
                      set score_normalized_sector = (score * 100)/(select max(score) from t_mitigation_exp_insights where sector_id = ? and year =?)\
                      where sector_id = ? and year = ?'

        cursor = self.dbConnection.cursor()
        cursor.execute(sql_update, sector_id, year, sector_id, year)
        self.dbConnection.commit()
        cursor.close()

        sql_delete = 'delete from t_sector_exp_mitigation_insights where sector_id =? and year = ?'
        cursor = self.dbConnection.cursor()
        cursor.execute(sql_delete, sector_id, year)
        self.dbConnection.commit()
        cursor.close()

        sql_insert = 'INSERT into t_sector_exp_mitigation_insights(sector_id,year,esg_category_name,exposure_path_name,\
                             mitigation_class,mitigation_sub_class,cluster_count_all,score,score_normalized,added_dt,added_by,modify_dt,modify_by)\
                    SELECT   insights.sector_id,insights.year Year,esg.esg_category_name ESG_Category,  exp.exposure_path_name Exposure_Pathway,\
                             mit.class_name,mit.sub_class_name, count(*) Pathways, AVG(insights.score_normalized_sector) Score, NULL, CURRENT_TIMESTAMP, ?,CURRENT_TIMESTAMP, ?\
                    FROM t_mitigation_exp_insights insights\
                        INNER JOIN t_exposure_pathway exp on exp.exposure_path_id = insights.exposure_path_id\
                        inner join t_impact_category imp on exp.impact_category_id = imp.impact_category_id\
                        inner join t_esg_category esg on imp.esg_category_id = esg.esg_category_id\
                        INNER JOIN t_key_word_hits hits on insights.mitigation_keyword_hit_id = hits.key_word_hit_id\
                        INNER JOIN t_mitigation mit on hits.dictionary_id = mit.dictionary_id\
                WHERE insights.sector_id = ? and insights.year = ?\
                GROUP by insights.sector_id,  insights.year,  esg.esg_category_name, exp.exposure_path_name, mit.class_name,mit.sub_class_name'

        cursor = self.dbConnection.cursor()
        cursor.execute(sql_insert, 'MOHAN HANUMANTHA',
                       'MOHAN HANUMANTHA', sector_id, year)
        self.dbConnection.commit()
        cursor.close()

        # Update Cluster Count
        # print('updating cluster count')
        sql_update_cluster = 'update t_sector_exp_mitigation_insights set cluster_count = cluster_count_all/(select count(document_id) from t_document doc inner join t_sec_company_sector_map map on doc.company_name = map.company_name where map.sector_id = ? and  doc.year = ?)\
                        where  sector_id = ? and year = ?'

        cursor = self.dbConnection.cursor()
        cursor.execute(sql_update_cluster, sector_id, year, sector_id, year)
        self.dbConnection.commit()
        cursor.close()

        # Normalize Score
        sql_update_normalize_score = 'update t_sector_exp_mitigation_insights\
                                   set score_normalized = (score * 100)/(select max(score) from t_sector_exp_mitigation_insights where sector_id = ? and year =?)\
                                   where sector_id = ? and year = ?'
        cursor = self.dbConnection.cursor()
        cursor.execute(sql_update_normalize_score,
                       sector_id, year, sector_id, year)
        self.dbConnection.commit()
        cursor.close()

# Build Reporting Tables

    def update_reporting_tables(self, sector, year, generate_exp_rpt_insights: bool, generate_int_rpt_insights: bool, generate_mit_rpt_insights: bool, update_all: bool, keywords_only=True):

        sector_id_sql = 'select lookups.data_lookups_id from t_data_lookups lookups where data_lookups_description = ?'
        cursor = self.dbConnection.cursor()
        cursor.execute(sector_id_sql, sector)
        sector_id = cursor.fetchone()[0]

        if (generate_exp_rpt_insights):
            self.update_exposure_reporting(
                sector_id=sector_id, year=year, update_all=update_all, keywords_only=keywords_only)

    def update_exposure_reporting(self, sector_id, year, update_all, keywords_only):
        if (update_all):
            if (not keywords_only):
                print('Update Exposure Report for All Sectors and years')

                sql_delete = 'truncate table t_rpt_exposure_pathway_insights'
                cursor = self.dbConnection.cursor()
                cursor.execute(sql_delete)
                self.dbConnection.commit()
                cursor.close()

                sql_insert = 'INSERT INTO t_rpt_exposure_pathway_insights( sector_id,company_name,year,document_id, content_type ,document_type,exposure_path_id, esg_category_name,exposure_path_name, cluster_count,score_normalized,\
                            unique_key_words,chat_gpt_text,added_dt,added_by,modify_dt,modify_by)\
                            \
                            SELECT comp.sector_id, doc.company_name,doc.year,doc.document_id, doc.content_type,lookups.data_lookups_description Document_Type,exp.exposure_path_id,esg.esg_category_name,exp.exposure_path_name,\
                                    count(*), AVG(insights.score_normalized) , NULL,NULL,CURRENT_TIMESTAMP,?, CURRENT_TIMESTAMP,?\
                            FROM t_exposure_pathway_insights insights\
                                    inner join t_exposure_pathway exp on exp.exposure_path_id = insights.exposure_path_id\
                                    inner join t_impact_category imp on exp.impact_category_id = imp.impact_category_id\
                                    inner join t_esg_category esg on imp.esg_category_id = esg.esg_category_id\
                                    inner join t_document doc on doc.document_id = insights.document_id\
                                    inner join t_data_lookups lookups on lookups.data_lookups_id = doc.content_type and lookups.data_lookups_group_id = 1\
                                    inner join t_sec_company_sector_map comp on doc.company_name = comp.company_name\
                            GROUP by comp.sector_id, doc.company_name,doc.year,doc.document_id,doc.content_type,lookups.data_lookups_description,esg.esg_category_name,exp.exposure_path_id,exp.exposure_path_name\
                            ORDER BY comp.sector_id, doc.company_name,doc.year,doc.document_id,doc.content_type,lookups.data_lookups_description,esg.esg_category_name,exp.exposure_path_id,exp.exposure_path_name\
                            '
                cursor = self.dbConnection.cursor()
                cursor.execute(sql_insert, 'Mohan Hanumantha',
                               'Mohan Hanumantha')
                self.dbConnection.commit()
                cursor.close()

            # Update Unique Keywords for each exposure pathway insight

            sector_year_list = []

            sector_year_list = self.get_sector_id_year_list()
            sector_year: SectorYearDBEntity
            for sector_year in sector_year_list:
                self.update_exposure_rpt_unique_keywordlist(
                    sector_year.SectorId, sector_year.Year)

        else:
            if (not keywords_only):

                print('Updating Exposure Report for Sector:' +
                      str(sector_id)+', Year:'+str(year))

                sql_delete = 'delete from t_rpt_exposure_pathway_insights where sector_id =? and year = ?'
                cursor = self.dbConnection.cursor()
                cursor.execute(sql_delete, sector_id, year)
                self.dbConnection.commit()
                cursor.close()
                sql_insert = 'INSERT INTO t_rpt_exposure_pathway_insights( sector_id,company_name,year,document_id, content_type ,document_type,exposure_path_id, esg_category_name,exposure_path_name, cluster_count,score_normalized,\
                            unique_key_words,chat_gpt_text,added_dt,added_by,modify_dt,modify_by)\
                            \
                            SELECT comp.sector_id, doc.company_name,doc.year,doc.document_id, doc.content_type,lookups.data_lookups_description Document_Type,exp.exposure_path_id,esg.esg_category_name,exp.exposure_path_name,\
                                    count(*), AVG(insights.score_normalized) , NULL,NULL,CURRENT_TIMESTAMP,?, CURRENT_TIMESTAMP,?\
                            FROM t_exposure_pathway_insights insights\
                                    inner join t_exposure_pathway exp on exp.exposure_path_id = insights.exposure_path_id\
                                    inner join t_impact_category imp on exp.impact_category_id = imp.impact_category_id\
                                    inner join t_esg_category esg on imp.esg_category_id = esg.esg_category_id\
                                    inner join t_document doc on doc.document_id = insights.document_id and doc.year = ?\
                                    inner join t_data_lookups lookups on lookups.data_lookups_id = doc.content_type and lookups.data_lookups_group_id = 1\
                                    inner join t_sec_company_sector_map comp on doc.company_name = comp.company_name and  comp.sector_id = ?\
                            GROUP by comp.sector_id, doc.company_name,doc.year,doc.document_id,doc.content_type,lookups.data_lookups_description,esg.esg_category_name,exp.exposure_path_id,exp.exposure_path_name\
                            ORDER BY comp.sector_id, doc.company_name,doc.year,doc.document_id,doc.content_type,lookups.data_lookups_description,esg.esg_category_name,exp.exposure_path_id,exp.exposure_path_name\
                            '
                cursor = self.dbConnection.cursor()
                cursor.execute(sql_insert, 'Mohan Hanumantha',
                               'Mohan Hanumantha', year, sector_id)
                self.dbConnection.commit()
                cursor.close()

            self.update_exposure_rpt_unique_keywordlist(sector_id, year)

    def update_exposure_rpt_unique_keywordlist(self, sector_id, year):
        print('Updating Unique Keywords for sector id:' +
              str(sector_id)+'  Year:'+str(year))
        # Update Unique Keywords in the list

        rpt_exp_list = []

        exp_rpt_sql = 'select unique_key, document_id, exposure_path_id from t_rpt_exposure_pathway_insights where sector_id = ? and year = ?'

        try:
            cursor = self.dbConnection.cursor()
            cursor.execute(exp_rpt_sql, sector_id, year)
            rows = cursor.fetchall()
            for row in rows:
                rpt_exp_list.append(
                    Reporting_DB_Entity(
                        unique_key=row.unique_key,
                        DocumentId=row.document_id,
                        ExposurePathId=row.exposure_path_id)
                )

        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

        for exp_rpt_line_item in rpt_exp_list:

            cursor = self.dbConnection.cursor()
            unique_keyword_list = ''
            keyword_sql = 'select distinct key_word1 keyword from t_exposure_pathway_insights where exposure_path_id = ? and document_id = ?\
                            UNION\
                            select distinct key_word2 keyword from t_exposure_pathway_insights where exposure_path_id = ? and document_id = ?\
                            '
            cursor.execute(
                keyword_sql, exp_rpt_line_item.ExposurePathId, exp_rpt_line_item.DocumentId, exp_rpt_line_item.ExposurePathId, exp_rpt_line_item.DocumentId)

            rows = cursor.fetchall()
            for row in rows:
                unique_keyword_list = unique_keyword_list + row.keyword + ','

            unique_keyword_list = unique_keyword_list.rstrip(',')
            sql_update = 'update t_rpt_exposure_pathway_insights set unique_key_words = ? where unique_key =?'
            cursor = self.dbConnection.cursor()
            cursor.execute(sql_update, unique_keyword_list,
                           exp_rpt_line_item.unique_key)
            cursor.close()
        self.dbConnection.commit()


# InsightGeneratorDBManager("Test").update_exposure_rpt_unique_keywordlist(1002,2023)
