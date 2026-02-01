import psycopg2
import psycopg2.extras
import datetime as dt
import numpy as np
from DBEntities.DocumentHeaderEntity import DocHeaderEntity
from DBEntities.DictionaryEntity import DictionaryEntity
from DBEntities.ProximityEntity import ProximityEntity
from DBEntities.ProximityEntity import KeyWordLocationsEntity
from DBEntities.ProximityEntity import Insight
from DBEntities.ProximityEntity import MitigationExpIntInsight
from DBEntities.ProximityEntity import ExpIntInsight
from DBEntities.ProximityEntity import DocumentEntity
from Utilities.LoggingServices import logGenerator
from DBEntities.DashboardDBEntitties import SectorYearDBEntity, Reporting_DB_Entity
from Utilities.Lookups import Lookups, DB_Connection
import time

import sys
from pathlib import Path
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))


INSIGHT_SCORE_THRESHOLD = 0
EXP_INT_MITIGATION_THRESHOLD = 10


PARM_LOGFILE = (
    r'/Users/mohanganadal/Data Company/Text Processing/Programs/DocumentProcessor/Log/InsightGenLog/InsighDBtLog')
DEV_DB_CONNECTION_STRING = DB_Connection().DEV_DB_CONNECTION_STRING
DB_LOGGING_ENABLED = True


class InsightGeneratorDBManager:

    def __init__(self, database_context: None) -> None:
        import os

        # Check if database is disabled for testing
        db_conn = DB_Connection()
        if db_conn.DEV_DB_CONNECTION_STRING is None:
            self.dbConnection = None
            self.database_disabled = True
            self.d_next_seed = 0
            self.batch_id = 0
            print(
                "⚠️  InsightGeneratorDBManager: Database operations disabled for local testing")
            return

        self.database_disabled = False
        connection_string = ''

        if (database_context == 'Development'):
            connection_string = DEV_DB_CONNECTION_STRING
        elif (database_context == 'Test'):
            connection_string = DEV_DB_CONNECTION_STRING  # Use same for now
        else:
            raise Exception("Database context Undefined")

        try:
            self.dbConnection = psycopg2.connect(connection_string)
        except Exception as e:
            print(
                f"⚠️  InsightGeneratorDBManager database connection failed: {str(e)}")
            self.dbConnection = None
            self.database_disabled = True

        self.d_next_seed = 0
        self.batch_id = 0

        self.log_file_path = f'{PARM_LOGFILE}_{dt.datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
        self.log_generator = logGenerator(self.log_file_path)

    def convert_numpy_types(self, value):
        """
        Convert numpy types to Python native types for PostgreSQL compatibility

        Args:
            value: Value that might be a numpy type

        Returns:
            Python native type
        """
        # Handle None values first
        if value is None:
            return None

        # Handle numpy types
        if isinstance(value, np.integer):
            return int(value)
        elif isinstance(value, np.floating):
            return float(value)
        elif isinstance(value, np.ndarray):
            return value.tolist()
        elif isinstance(value, np.str_):
            return str(value)
        elif hasattr(np, 'unicode_') and isinstance(value, np.unicode_):
            # Handle older NumPy versions that still have np.unicode_
            return str(value)
        else:
            return value

    def get_company_list(self, sic_code: None):  # , company_name:None):

        company_list = []

        sic_code = sic_code+'%'
        # company_name = '%'+company_name+'%'

        sql = "SELECT sic.sic_code, sic.industry_title,header.conformed_name, header.form_type,header.document_id, header.document_name, header.reporting_year, header.reporting_quarter\
               FROM t_sic_codes sic INNER JOIN t_sec_document_header header ON sic.sic_code = header.sic_code_4_digit \
                    and header.reporting_year = 2022\
                    where sic.industry_title like %s \
                    and form_type ='10-K' and reporting_quarter =1\
                    order by sic.sic_code"

        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            # pyright: ignore[reportUnknownArgumentType] # , company_name)
            cursor.execute(sql, sic_code)
            rows = cursor.fetchall()
            for row in rows:
                doc_header_entity = DocHeaderEntity()
                # document_id
                doc_header_entity.document_id = row['document_id']
                # document_name
                doc_header_entity.document_name = row['document_name']
                # reporting_year
                doc_header_entity.reporting_year = row['reporting_year']
                # reporting_quarter
                doc_header_entity.reporting_quarter = row['reporting_quarter']
                # conformed_name
                doc_header_entity.conformed_name = row['conformed_name']
                # sic_code
                doc_header_entity.sic_code = row['sic_code']
                # form_type
                doc_header_entity.form_type = row['form_type']
                # pyright: ignore[reportUnknownMemberType]
                company_list.append(doc_header_entity)

            cursor.close()

            # print("Record inserted successfully!")

        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc
        return company_list

        # type: ignore
       # return compan        cursor.execute(sql, (((company_name, reporting_year))))        cursor.execute(sql, (((company_name, reporting_year))))        cursor.execute(sql, (((company_name, reporting_year))))y_list

    def get_company_id_by_Name(self,  company_name: None, reporting_year: None):

        company_id: int
        sql = "SELECT comp.company_id\
               FROM t_sec_company comp\
               where comp.conformed_name = %s \
                     and comp.reporting_year = %s"

        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            # , company_name)
            cursor.execute(sql, (((company_name, reporting_year))))
            rows = cursor.fetchone()

            company_id = rows['company_id']
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
            sql = "select max(unique_key) unique_key from t_exposure_pathway_insights"
        elif (save_type == Lookups().Internalization_Save):
            sql = "select max(unique_key) unique_key from t_internalization_insights"
        elif (save_type == Lookups().Mitigation_Exp_Insight_Type):
            sql = "select max(unique_key) unique_key from t_mitigation_exp_insights"
        elif (save_type == Lookups().Mitigation_Int_Insight_Type):
            sql = "select max(unique_key) unique_key from t_mitigation_int_insights"
        elif (save_type == Lookups().Exp_Int_Insight_Type):
            sql = "select max(unique_key) unique_key from t_exp_int_insights"
        elif (save_type == Lookups().Mitigation_Exp_INT_Insight_Type):
            sql = "select max(unique_key) unique_key from t_mitigation_exp_int_insights"

        cursor = self.dbConnection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute(sql)

        current_db_seed = cursor.fetchone()['unique_key']
        if (current_db_seed):
            self.d_next_seed = current_db_seed+1
            return self.d_next_seed
        else:
            self.d_next_seed = 1001
            return self.d_next_seed
        cursor.close()

    def normalize_document_score(self, dictionary_type: int, document_id: int):

        if (dictionary_type == Lookups().Exposure_Pathway_Dictionary_Type):
            sql = "update t_exposure_pathway_insights set score_normalized = (score * 100)/(select max(score) from t_exposure_pathway_insights where document_id = %s) where document_id = %s"
        elif (dictionary_type == Lookups().Internalization_Dictionary_Type):
            sql = "update t_internalization_insights set score_normalized = (score * 100)/(select max(score) from t_internalization_insights where document_id = %s) where document_id = %s"
        elif (dictionary_type == Lookups().Mitigation_Exp_Insight_Type):
            sql = "update t_mitigation_exp_insights set score_normalized = (score * 100)/(select max(score) from t_mitigation_exp_insights where document_id = %s) where document_id = %s"
        elif (dictionary_type == Lookups().Mitigation_Int_Insight_Type):
            sql = "update t_mitigation_int_insights set score_normalized = (score * 100)/(select max(score) from t_mitigation_int_insights where document_id = %s) where document_id = %s"
        elif (dictionary_type == Lookups().Exp_Int_Insight_Type):
            sql = "update t_exp_int_insights set score_normalized = (score * 100)/(select max(score) from t_exp_int_insights where document_id = %s) where document_id = %s"
        elif (dictionary_type == Lookups().Mitigation_Exp_INT_Insight_Type):
            sql = "update t_mitigation_exp_int_insights set score_normalized = (score * 100)/(select max(score) from t_mitigation_exp_int_insights where document_id = %s) where document_id = %s"

        try:
            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            # Fix: Pass parameters as tuple
            cursor.execute(sql, (document_id, document_id))
            self.dbConnection.commit()
            cursor.close()
        except Exception as exc:
            self.dbConnection.rollback()
            print(f"Error: {str(exc)}")
            raise exc

    def get_keyword_location_list(self, dictionary_type=0, dictionary_id=0, document_id=0):

        keyword_list = []
        sql = 'select key_word_hit_id, key_word, locations, frequency, dictionary_type, dictionary_id, document_id, exposure_path_id, internalization_id \
               from t_key_word_hits \
               where dictionary_type = %s and dictionary_id = %s and document_id = %s\
               order by key_word_hit_id'
        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sql, (dictionary_type, dictionary_id, document_id))
            rows = cursor.fetchall()
            for row in rows:

                keyword_loc_entity = KeyWordLocationsEntity()
                keyword_loc_entity.key_word_hit_id = row['key_word_hit_id']
                keyword_loc_entity.key_word = row['key_word']
                keyword_loc_entity.locations = row['locations']
                keyword_loc_entity.frequency = row['frequency']
                keyword_loc_entity.dictionary_type = row['dictionary_type']
                keyword_loc_entity.dictionary_id = row['dictionary_id']
                keyword_loc_entity.exposure_path_id = row['exposure_path_id']
                keyword_loc_entity.internalization_id = row['internalization_id']
                keyword_list.append(keyword_loc_entity)

            cursor.close()

            # print("Record inserted successfully!")

        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

        return keyword_list

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
            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row in rows:
                keyword_loc_entity = KeyWordLocationsEntity()
                keyword_loc_entity.document_id = row['document_id']
                keyword_loc_entity.year = row['year']
                document_list.append(keyword_loc_entity)
            cursor.close()

        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc
        print(
            f"Total unprocessed documents for insight generation: {len(document_list)}")
        return document_list

    def get_keyword_hits_for_insight_gen(self, dictionary_type: int, document_id: int):

        document_keyword_list = []

        sql = f"select distinct hits.document_id, hits.dictionary_id, hits.document_name,hits.dictionary_type \
            from t_key_word_hits hits \
            where  hits.dictionary_type = %s and hits.document_id = %s"
        try:
            # Execute the SQL query
            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sql, (((dictionary_type, document_id))))
            rows = cursor.fetchall()
            for row in rows:
                keyword_loc_entity = KeyWordLocationsEntity()
                keyword_loc_entity.dictionary_id = row['dictionary_id']
                keyword_loc_entity.document_id = row['document_id']
                keyword_loc_entity.document_name = row['document_name']
                keyword_loc_entity.dictionary_type = row['dictionary_type']
                document_keyword_list.append(keyword_loc_entity)
            cursor.close()

        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

        return document_keyword_list

    def get_sector_id(self, document_id):

        sql = 'select map.sector_id sector_id\
            from t_sec_company_sector_map map \
            inner join t_document doc  on map.company_name = doc.company_name and doc.document_id = %s'

        try:
            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)  # ADD cursor creation
            cursor.execute(sql, (document_id,))
            result = cursor.fetchone()
            if result:
                sector_id = result['sector_id']  # Use dictionary access
                cursor.close()
                return sector_id
            else:
                cursor.close()
                print(
                    'Sector Not Mapped for the Company: Please check t_sec_company_sector_map')
                raise Exception(
                    'Sector Not Mapped for the Company: Please check t_sec_company_sector_map')
        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

    def insert_key_word_hits_to_db(self, company_id: int, document_id: str, document_name: str, reporting_year: int, dictionary_id: int, key_word: str, locations: str, frequency: int, dictionary_type: int, exposure_path_id: int, internalization_id: int, impact_category_id: int, esg_category_id: int, batch_id: int):

        # Create a cursor object to execute SQL queries
        cursor = self.dbConnection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        # Construct the INSERT INTO statement

        sql = f"INSERT INTO t_key_word_hits( \
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
                  key_word + " , ((Document ID:"+str(document_id,))
            # print('Location Size:'+ str(len(locations)))
            # print(locations)
            print(f"Error: {str(exc)}")
            raise exc

            # Close the cursor and connection
            cursor.close()

            pass

        start_time = time.time()

        insight: Insight
        self.d_next_seed = 0
        total_records_added_to_db = 0
        sector_id = self.get_sector_id(document_id)

        # Telemetrics initialization
        db_operation_time = 0
        preparation_time = 0
        if (DB_LOGGING_ENABLED):
            self.log_generator.log_details(
                f"🔄 Starting save_insights for {len(insightList)} records...")
        prep_start = time.time()

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
            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            # Construct the INSERT INTO statement

            if (dictionary_type == Lookups().Exposure_Pathway_Dictionary_Type):
                sql = f"INSERT INTO t_exposure_pathway_insights( \
                        document_id, sector_id, document_name, key_word_hit_id1, key_word_hit_id2,key_word1, key_word2,score,\
                    factor1, factor2,exposure_path_id, added_dt,added_by ,modify_dt,modify_by, year\
                    )\
                        VALUES\
                        ({document_id},{sector_id},N'{document_name}',{key_word_hit_id1},{key_word_hit_id2},N'{key_word1}',N'{key_word2}',{score},\
                        {factor1}, {factor2},{exposure_path_id},CURRENT_TIMESTAMP, N'Mohan Hanumantha',CURRENT_TIMESTAMP, N'Mohan Hanumantha',{year})"

            elif (dictionary_type == Lookups().Internalization_Dictionary_Type):
                sql = f"INSERT INTO t_internalization_insights( \
                    document_id,sector_id, document_name, key_word_hit_id1, key_word_hit_id2,key_word1, key_word2,score,\
                    factor1, factor2,internalization_id, added_dt,added_by ,modify_dt,modify_by, year\
                    )\
                        VALUES\
                        ({document_id},{sector_id},N'{document_name}',{key_word_hit_id1},{key_word_hit_id2},N'{key_word1}',N'{key_word2}',{score},\
                        {factor1}, {factor2},{internalization_id},CURRENT_TIMESTAMP, N'Mohan Hanumantha',CURRENT_TIMESTAMP, N'Mohan Hanumantha',{year})"

            elif (dictionary_type == Lookups().Mitigation_Exp_Insight_Type):
                mitigation_keyword_hit_id = insight.mitigation_keyword_hit_id
                mitigation_keyword = insight.mitigation_keyword
                # int_unique_key = self.get_next_surrogate_key(
                #     Lookups().Mitigation_Exp_Insight_Type)
                sql = f"INSERT INTO t_mitigation_exp_insights( \
                    document_id, sector_id,document_name, key_word_hit_id1, key_word_hit_id2,key_word1, key_word2,mitigation_keyword_hit_id,mitigation_keyword,\
                    score,factor1, factor2, exposure_path_id,added_dt,added_by ,modify_dt,modify_by,year\
                    )\
                        VALUES\
                        ({document_id},{sector_id},N'{document_name}',{key_word_hit_id1},{key_word_hit_id2},N'{key_word1}',N'{key_word2}',{mitigation_keyword_hit_id},N'{mitigation_keyword}',\
                        {score},{factor1}, {factor2},{exposure_path_id},CURRENT_TIMESTAMP, N'Mohan Hanumantha',CURRENT_TIMESTAMP, N'Mohan Hanumantha',{year})"

            elif (dictionary_type == Lookups().Mitigation_Int_Insight_Type):
                mitigation_keyword_hit_id = insight.mitigation_keyword_hit_id
                mitigation_keyword = insight.mitigation_keyword
                # int_unique_key = self.get_next_surrogate_key(
                #     Lookups().Mitigation_Int_Insight_Type)

                sql = f"INSERT INTO t_mitigation_int_insights( \
                    document_id,sector_id, document_name, key_word_hit_id1, key_word_hit_id2,key_word1, key_word2,mitigation_keyword_hit_id,mitigation_keyword,\
                score,factor1, factor2, internalization_id, added_dt,added_by ,modify_dt,modify_by, year\
                )\
                    VALUES\
                    ({document_id},{sector_id},N'{document_name}',{key_word_hit_id1},{key_word_hit_id2},N'{key_word1}',N'{key_word2}',{mitigation_keyword_hit_id},N'{mitigation_keyword}',\
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
                if (DB_LOGGING_ENABLED):
                    self.log_generator.log_details(
                        f"Error in save_insights: {str(exc)}")

                print(f"Error: {str(exc)}")
                raise exc
            db_end = time.time()
            db_operation_time += (db_end - db_start)
            prep_start = time.time()
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

    def save_insights(self, insightList, dictionary_type, document_id, year=0):
        """
        Save insights with telemetrics tracking using centralized method
        """
        start_time = time.time()
        insight: Insight
        self.d_next_seed = 0
        total_records_added_to_db = 0
        sector_id = self.get_sector_id(document_id)

        # Telemetrics initialization
        db_operation_time = 0
        preparation_time = 0

        if (DB_LOGGING_ENABLED):
            self.log_generator.log_details(
                f"🔄 Starting save_insights for {len(insightList)} records...")

        prep_start = time.time()

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

            prep_end = time.time()
            preparation_time += (prep_end - prep_start)

            # Database operation timing
            db_start = time.time()

            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)

            if (dictionary_type == Lookups().Exposure_Pathway_Dictionary_Type):
                sql = f"INSERT INTO t_exposure_pathway_insights( \
                        document_id, sector_id, document_name, key_word_hit_id1, key_word_hit_id2,key_word1, key_word2,score,\
                    factor1, factor2,exposure_path_id, added_dt,added_by ,modify_dt,modify_by, year\
                    )\
                        VALUES\
                        ({document_id},{sector_id},N'{document_name}',{key_word_hit_id1},{key_word_hit_id2},N'{key_word1}',N'{key_word2}',{score},\
                        {factor1}, {factor2},{exposure_path_id},CURRENT_TIMESTAMP, N'Mohan Hanumantha',CURRENT_TIMESTAMP, N'Mohan Hanumantha',{year})"

            elif (dictionary_type == Lookups().Internalization_Dictionary_Type):
                sql = f"INSERT INTO t_internalization_insights( \
                    document_id,sector_id, document_name, key_word_hit_id1, key_word_hit_id2,key_word1, key_word2,score,\
                    factor1, factor2,internalization_id, added_dt,added_by ,modify_dt,modify_by, year\
                    )\
                        VALUES\
                        ({document_id},{sector_id},N'{document_name}',{key_word_hit_id1},{key_word_hit_id2},N'{key_word1}',N'{key_word2}',{score},\
                        {factor1}, {factor2},{internalization_id},CURRENT_TIMESTAMP, N'Mohan Hanumantha',CURRENT_TIMESTAMP, N'Mohan Hanumantha',{year})"

            elif (dictionary_type == Lookups().Mitigation_Exp_Insight_Type):
                mitigation_keyword_hit_id = insight.mitigation_keyword_hit_id
                mitigation_keyword = insight.mitigation_keyword
                sql = f"INSERT INTO t_mitigation_exp_insights( \
                    document_id, sector_id,document_name, key_word_hit_id1, key_word_hit_id2,key_word1, key_word2,mitigation_keyword_hit_id,mitigation_keyword,\
                    score,factor1, factor2, exposure_path_id,added_dt,added_by ,modify_dt,modify_by,year\
                    )\
                        VALUES\
                        ({document_id},{sector_id},N'{document_name}',{key_word_hit_id1},{key_word_hit_id2},N'{key_word1}',N'{key_word2}',{mitigation_keyword_hit_id},N'{mitigation_keyword}',\
                        {score},{factor1}, {factor2},{exposure_path_id},CURRENT_TIMESTAMP, N'Mohan Hanumantha',CURRENT_TIMESTAMP, N'Mohan Hanumantha',{year})"

            elif (dictionary_type == Lookups().Mitigation_Int_Insight_Type):
                mitigation_keyword_hit_id = insight.mitigation_keyword_hit_id
                mitigation_keyword = insight.mitigation_keyword
                sql = f"INSERT INTO t_mitigation_int_insights( \
                    document_id,sector_id, document_name, key_word_hit_id1, key_word_hit_id2,key_word1, key_word2,mitigation_keyword_hit_id,mitigation_keyword,\
                score,factor1, factor2, internalization_id, added_dt,added_by ,modify_dt,modify_by, year\
                )\
                    VALUES\
                    ({document_id},{sector_id},N'{document_name}',{key_word_hit_id1},{key_word_hit_id2},N'{key_word1}',N'{key_word2}',{mitigation_keyword_hit_id},N'{mitigation_keyword}',\
                    {score},{factor1}, {factor2},{internalization_id},CURRENT_TIMESTAMP, N'Mohan Hanumantha',CURRENT_TIMESTAMP, N'Mohan Hanumantha',{year})"

            try:
                cursor.execute(sql)
                total_records_added_to_db = total_records_added_to_db + 1
                if (total_records_added_to_db % 50 == 0):
                    self.dbConnection.commit()

            except Exception as exc:
                self.dbConnection.rollback()
                if (DB_LOGGING_ENABLED):
                    self.log_generator.log_details(
                        f"Error in save_insights: {str(exc)}")
                raise exc

            db_end = time.time()
            db_operation_time += (db_end - db_start)
            prep_start = time.time()

        # Final commit
        commit_start = time.time()
        if (total_records_added_to_db > 0):
            self.dbConnection.commit()
            cursor.close()
        commit_end = time.time()

        # Calculate total time and log telemetrics
        total_time = time.time() - start_time
        commit_time = commit_end - commit_start

        # Additional metrics specific to this operation
        additional_metrics = {
            "Dictionary Type": dictionary_type,
            "Document ID": document_id,
            "Year": year,
            "Batch Commit Frequency": "Every 50 records"
        }

        # Use centralized telemetrics method
        self._log_telemetrics(
            operation_name="save_insights",
            total_records=total_records_added_to_db,
            total_time=total_time,
            preparation_time=preparation_time,
            db_operation_time=db_operation_time,
            commit_time=commit_time,
            additional_metrics=additional_metrics
        )

    def cleanup_insights_for_document(self, dictionary_type, document_list):

        l_str_document_list_for_deletion: str
        first_element = True
        for document_item in document_list:
            # print(str(document_item.document_id))
            if (first_element):
                l_str_document_list_for_deletion = '('+str(
                    document_item.document_id)
                first_element = False
            else:
                l_str_document_list_for_deletion = l_str_document_list_for_deletion + \
                    ',' + str(document_item.document_id)

        l_str_document_list_for_deletion = l_str_document_list_for_deletion + ')'

        # print('Deletion String:')
        # print(l_str_document_list_for_deletion)

        cursor = self.dbConnection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        if (dictionary_type == Lookups().Exposure_Pathway_Dictionary_Type):
            sql = f"delete from t_exposure_pathway_insights where document_id in " + \
                l_str_document_list_for_deletion

        elif (dictionary_type == Lookups().Internalization_Dictionary_Type):
            sql = f"delete from t_internalization_insights where document_id in" + \
                l_str_document_list_for_deletion

        elif (dictionary_type == Lookups().Exp_Int_Insight_Type):
            sql = f"delete from  t_exp_int_insights where document_id in" + \
                l_str_document_list_for_deletion

        elif (dictionary_type == Lookups().Mitigation_Exp_Insight_Type):
            sql = f"delete from  t_mitigation_exp_insights where document_id in" + \
                l_str_document_list_for_deletion

        elif (dictionary_type == Lookups().Mitigation_Int_Insight_Type):
            sql = f"delete from t_mitigation_int_insights where document_id in" + \
                l_str_document_list_for_deletion

        elif (dictionary_type == Lookups().Mitigation_Exp_INT_Insight_Type):
            sql = f"delete from t_mitigation_exp_int_insights where document_id in" + \
                l_str_document_list_for_deletion

        print(sql)

        try:
            # Execute the SQL query
            cursor.execute(sql)
            self.dbConnection.commit()

        except Exception as exc:
            # Rollback the transaction if any error occurs
            self.dbConnection.rollback()
            print(f"Error: {str(exc)}")
            raise exc

    def save_key_word_hits(self, proximity_entity_list, company_id: int, document_id: int, document_name: str, reporting_year: int, dictionary_type: int, batch_id: int):

        # delete from existing records for the same document
        try:
            sql = 'delete from t_key_word_hits where document_id = %s and dictionary_type = %s'
            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sql, (document_id, dictionary_type))
            self.dbConnection.commit()
            # print("delete fromd previous search data for document:" + document_name +", dictionary type:" + str(dictionary_type))
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
        # print('Total Proximity Entities to process:' +
        #       str(len(proximity_entity_list)))
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

    def update_insights_generated_from_keyword_hits_batch(self, dictionary_type=0, dictionary_id=0, document_id=0, suuccess_ind=1):

        # sql = f"update t_key_word_hits set \
        #         insights_generated = 1 ,modify_dt = CURRENT_TIMESTAMP ,modify_by = N'Mohan Hanumantha'\
        #         where batch_id ={batch_id} and insights_generated = 0 and dictionary_type ={dictionary_type} and dictionary_id ={dictionary_id} and document_id ={document_id}"

        if (dictionary_type == Lookups().Exposure_Pathway_Dictionary_Type):
            sql = f"update t_document set exp_insights_generated_ind = {suuccess_ind} \
                    ,modify_dt = CURRENT_TIMESTAMP ,modify_by = N'Mohan Hanumantha'\
                    where document_id ={document_id}"
        elif (dictionary_type == Lookups().Internalization_Dictionary_Type):
            sql = f"update t_document set int_insights_generated_ind = {suuccess_ind} \
                    ,modify_dt = CURRENT_TIMESTAMP ,modify_by = N'Mohan Hanumantha'\
                    where document_id ={document_id}"
        try:
            # Execute the SQL query
            # Create a cursor object to execute SQL queries
            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sql)
            self.dbConnection.commit()
            cursor.close()
        except Exception as exc:
            # Rollback the transaction if any error occurs
            self.dbConnection.rollback()
            print(f"Error: {str(exc)}")
            raise exc

            # Close the cursor and connection

    def update_validation_keywords_generated_status(self, document_list, dictionary_type, status):
        if (dictionary_type == Lookups().Exposure_Pathway_Dictionary_Type):
            sql = f"UPDATE t_document set exp_validation_completed_ind = %s where document_id = %s"
        elif (dictionary_type == Lookups().Internalization_Dictionary_Type):
            sql = f"UPDATE t_document set int_validation_completed_ind = %s where document_id = %s"
        elif (dictionary_type == Lookups().Mitigation_Dictionary_Type):
            sql = f"UPDATE t_document set mit_validation_completed_ind = %s where document_id = %s"

        for document in document_list:
            # print('Document ID:'+str(document.document_id) +', Status:'+str(status))
            # print(sql)
            try:
                cursor = self.dbConnection.cursor(
                    cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute(sql, (((status, document.document_id))))
                self.dbConnection.commit()
                cursor.close()

            except Exception as exc:
                self.dbConnection.rollback()
                print(f"Error: {str(exc)}")
                raise exc

    def update_validation_completed_status(self):
        # print("✅ Processed Dictionary Terms Successfully - DEBUG INSIDE DB MGR")

        exp_sql = f"UPDATE t_document set \
                    exp_validation_completed_ind = 1,modify_dt = CURRENT_TIMESTAMP \
                where \
                    exp_validation_completed_ind in(0,2) and exp_pathway_keyword_search_completed_ind = 0"

        int_sql = f"UPDATE t_document set \
                    int_validation_completed_ind =1,modify_dt = CURRENT_TIMESTAMP \
                where \
                    int_validation_completed_ind in(0,2) and internalization_keyword_search_completed_ind = 0"

        mit_sql = f"UPDATE t_document set \
                    mit_validation_completed_ind = 1,modify_dt = CURRENT_TIMESTAMP \
                where \
                    mit_validation_completed_ind in(0,2) and mitigation_search_completed_ind = 0"
        try:
            # print(exp_sql)
            # print(int_sql)
            # print(mit_sql)
            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(exp_sql)
            cursor.execute(int_sql)
            cursor.execute(mit_sql)
            self.dbConnection.commit()
            cursor.close()

        except Exception as exc:
            self.dbConnection.rollback()
            print(f"Error: {str(exc)}")
            raise exc

    def update_validation_failed_status(self, document_id, dictionary_type):

        exp_sql = f"UPDATE t_document set exp_validation_completed_ind = 0 where document_id ={document_id}"
        int_sql = f"UPDATE t_document set int_validation_completed_ind = 0 where document_id ={document_id}"
        mit_sql = f"UPDATE t_document set  mit_validation_completed_ind = 0 where document_id ={document_id}"

        try:
            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)

            if (dictionary_type == Lookups().Exposure_Pathway_Dictionary_Type):
                cursor.execute(exp_sql)
            if (dictionary_type == Lookups().Internalization_Dictionary_Type):
                cursor.execute(int_sql)
            if (dictionary_type == Lookups().Internalization_Dictionary_Type):
                cursor.execute(mit_sql)
            self.dbConnection.commit()
            cursor.close()
        except Exception as exc:
            self.dbConnection.rollback()
            print(f"Error: {str(exc)}")
            raise exc

            # EXPOSURE PATHWAY

    def get_exp_dictionary_term_list(self):

        exp_dict_terms_list = []

        # sql = "select d.dictionary_id, ((d.keywords,d.exposure_path_id from t_exposure_pathway_dictionary d where d.dictionary_id = 1001"
        sql = "select esg.esg_category_id, imp.impact_category_id, exp.exposure_path_id, d.dictionary_id,d.keywords \
            from t_exposure_pathway_dictionary d INNER JOIN  t_exposure_pathway exp on d.exposure_path_id = exp.exposure_path_id\
                            INNER JOIN  t_impact_category imp on imp.impact_category_id = exp.impact_category_id\
                            INNER JOIN t_esg_category esg on esg.esg_category_id = imp.esg_category_id"
        #  where dictionary_id = 1005"
        # DEBUG COMMENT LINE ABOVE

        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sql)
            rows = cursor.fetchall()

            for row in rows:
                try:
                    exp_dict_terms_list.append(DictionaryEntity(
                        esg_category_id=row['esg_category_id'] if 'esg_category_id' in row else row[0],
                        impact_category_id=row['impact_category_id'] if 'impact_category_id' in row else row[1],
                        exposure_path_id=row['exposure_path_id'] if 'exposure_path_id' in row else row[2],
                        dictionary_id=row['dictionary_id'] if 'dictionary_id' in row else row[3],
                        keywords=row['keywords'] if 'keywords' in row else row[4])
                    )
                except Exception as e:
                    print(
                        f"Error accessing row data in get_exp_keywords: {e}")
                    print(
                        f"Row keys: {list(row.keys()) if hasattr(row, 'keys') else 'No keys method'}")
                    raise
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
            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)

            sql = "select doc.document_id, comp.company_id, doc.document_name, doc.company_name, doc.year, doc.batch_id \
                            from t_document doc, t_sec_company comp \
                            where \
                            doc.exp_pathway_keyword_search_completed_ind in(0,2) and doc.company_name = comp.conformed_name and doc.exp_validation_completed_ind=%s order by doc.document_id"

            cursor.execute(sql, (validation_completed_ind,))

            rows = cursor.fetchall()

            for row in rows:
                document_entity = DocumentEntity()
                # Use the actual column names from the database or fallback to index
                document_entity.document_id = row['document_id'] if 'document_id' in row else row[0]
                document_entity.document_name = row['document_name'] if 'document_name' in row else row[2]
                document_entity.company_name = row['company_name'] if 'company_name' in row else row[3]
                document_entity.company_id = row['company_id'] if 'company_id' in row else row[1]
                document_entity.year = row['year'] if 'year' in row else row[4]
                document_entity.batch_id = row['batch_id'] if 'batch_id' in row else row[5]
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

        sql = f"update t_document set exp_pathway_keyword_search_completed_ind ={completed_ind} \
                ,modify_dt = CURRENT_TIMESTAMP ,modify_by = N'Mohan Hanumantha'\
                where document_id ={document_id}"
        try:
            # Execute the SQL query
            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sql)
            self.dbConnection.commit()
            cursor.close()
        except Exception as exc:
            # Rollback the transaction if any error occurs
            self.dbConnection.rollback()
            print(f"Error: {str(exc)}")
            raise exc

            # Close the cursor and connection

    # INTERNALIZAITON

    def get_int_dictionary_term_list(self):

        int_dict_terms_list = []

        sql = "select d.dictionary_id, keywords, internalization_id from t_internalization_dictionary d"
        # where d.dictionary_id in(1004,1012)
        # DEBUG COMMENT LINE ABOVE
        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sql)
            rows = cursor.fetchall()

            # DEBUG: Print available columns
            # if rows and len(rows) > 0:
            #     print(
            #         f"Available columns in get_internalization_keywords: {list(rows[0].keys())}")

            for row in rows:
                try:
                    int_dict_terms_list.append(DictionaryEntity(
                        dictionary_id=row['dictionary_id'] if 'dictionary_id' in row else row[0],
                        keywords=row['keywords'] if 'keywords' in row else row[1],
                        internalization_id=row['internalization_id'] if 'internalization_id' in row else row[2]))
                except Exception as e:
                    print(f"Error in get_internalization_keywords: {e}")
                    print(
                        f"Row keys: {list(row.keys()) if hasattr(row, 'keys') else 'No keys method'}")
                    raise
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
            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            sql = "select doc.document_id, comp.company_id, doc.document_name, doc.company_name, doc.year, doc.batch_id \
                                from t_document doc, t_sec_company comp \
                                where \
                                doc.internalization_keyword_search_completed_ind in(0,2) and doc.company_name = comp.conformed_name and doc.int_validation_completed_ind =%s  order by doc.document_id"

            cursor.execute(sql, (validation_completed_ind,))
            rows = cursor.fetchall()
            for row in rows:
                document_entity = DocumentEntity()
                document_entity.document_id = row['document_id']
                document_entity.document_name = row['document_name']
                document_entity.company_name = row['company_name']
                document_entity.company_id = row['company_id']
                document_entity.year = row['year']
                document_entity.batch_id = row['batch_id']
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
        cursor = self.dbConnection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)

        sql = f"update t_document set internalization_keyword_search_completed_ind = {completed_ind} \
                ,modify_dt = CURRENT_TIMESTAMP ,modify_by = N'Mohan Hanumantha'\
                where document_id ={document_id}"
        try:
            # Execute the SQL query
            cursor.execute(sql)
            self.dbConnection.commit()
            # Close the cursor and connection
            cursor.close()
        except Exception as exc:
            # Rollback the transaction if any error occurs
            self.dbConnection.rollback()
            print(f"Error: {str(exc)}")
            raise exc
            # MITIGATION

    def get_mitigation_dictionary_term_list(self):

        mitigation_dict_terms_list = []

        sql = "select dictionary_id, keywords from t_mitigation"

        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor,)
            cursor.execute(sql)
            rows = cursor.fetchall()

            # DEBUG: Print available columns
            # if rows and len(rows) > 0:
            #     print(
            #         f"Available columns in get_mitigation_keywords: {list(rows[0].keys())}")

            for row in rows:
                try:
                    mitigation_dict_terms_list.append(DictionaryEntity(
                        dictionary_id=row['dictionary_id'] if 'dictionary_id' in row else row[0],
                        keywords=row['keywords'] if 'keywords' in row else row[1]))
                except Exception as e:
                    print(f"Error in get_mitigation_keywords: {e}")
                    print(
                        f"Row keys: {list(row.keys()) if hasattr(row, 'keys') else 'No keys method'}")
                    raise
            cursor.close()

        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

        return mitigation_dict_terms_list

    def get_mitigation_document_list(self, validation_mode: bool):
        document_list = []
        if (validation_mode):
            validation_completed_ind = 0
        else:
            validation_completed_ind = 1

        try:
            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            sql = "select doc.document_id, comp.company_id, doc.document_name, doc.company_name, doc.year, doc.batch_id \
                            from t_document doc, t_sec_company comp \
                            where \
                            doc.mitigation_search_completed_ind in(0,2) and doc.company_name = comp.conformed_name and doc.mit_validation_completed_ind=%s order by document_id"

            cursor.execute(sql, (validation_completed_ind,))

            rows = cursor.fetchall()
            for row in rows:
                document_entity = DocumentEntity()
                document_entity.document_id = row['document_id']
                document_entity.document_name = row['document_name']
                document_entity.company_name = row['company_name']
                document_entity.company_id = row['company_id']
                document_entity.year = row['year']
                document_entity.batch_id = row['batch_id']
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
        cursor = self.dbConnection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)

        sql = f"update t_document set mitigation_search_completed_ind = {completed_ind} \
                    ,modify_dt = CURRENT_TIMESTAMP ,modify_by = N'Mohan Hanumantha'\
                    where document_id ={document_id}"
        try:
            # Execute the SQL query
            cursor.execute(sql)
            self.dbConnection.commit()
            # Close the cursor and connection
            cursor.close()

        except Exception as exc:
            # Rollback the transaction if any error occurs
            self.dbConnection.rollback()
            print(f"Error: {str(exc)}")
            raise exc

        # TRIANGULATION

        # COMMON

    def update_triangulation_insights_generated_batch(self, dictionary_type, document_id, insights_generated=1):

        cursor = self.dbConnection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)

        # Create a cursor object to execute SQL queries
        if (dictionary_type == Lookups().Mitigation_Exp_Insight_Type):
            sql = f"update t_document set mitigation_exp_insights_generated = {insights_generated} \
                                ,modify_dt = CURRENT_TIMESTAMP ,modify_by = N'Mohan Hanumantha'\
                                where document_id ={document_id}"
        elif (dictionary_type == Lookups().Mitigation_Int_Insight_Type):
            sql = f"update t_document set mitigation_int_insights_generated = {insights_generated} \
                                ,modify_dt = CURRENT_TIMESTAMP ,modify_by = N'Mohan Hanumantha'\
                                where document_id ={document_id}"
        elif (dictionary_type == Lookups().Exp_Int_Insight_Type):
            sql = f"update t_document set int_exp_insights_generated = {insights_generated} \
                        ,modify_dt = CURRENT_TIMESTAMP ,modify_by = N'Mohan Hanumantha'\
                        where document_id ={document_id}"
        elif (dictionary_type == Lookups().Mitigation_Exp_INT_Insight_Type):
            sql = f"update t_document set mitigation_int_exp_insights_generated = {insights_generated} \
                        ,modify_dt = CURRENT_TIMESTAMP ,modify_by = N'Mohan Hanumantha'\
                        where document_id ={document_id}"
        try:
            # Execute the SQL query
            cursor.execute(sql)
            self.dbConnection.commit()
            # Close the cursor and connection
            cursor.close()
        except Exception as exc:
            # Rollback the transaction if any error occurs
            self.dbConnection.rollback()
            print(f"Error: {str(exc)}")
            raise exc

        # EXP MITIGATION

    def get_exp_mitigation_document_list(self):
        document_list = []
        try:
            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("select doc.document_id, comp.company_id, doc.document_name, doc.company_name, doc.year \
                                from t_document doc, t_sec_company comp \
                                where \
                                doc.mitigation_exp_insights_generated = 0 and doc.company_name = comp.conformed_name\
                                and doc.exp_insights_generated_ind = 1 and doc.mitigation_search_completed_ind = 1\
                            ")
            rows = cursor.fetchall()
            for row in rows:
                document_entity = DocumentEntity()
                document_entity.document_id = row['document_id']
                document_entity.document_name = row['document_name']
                document_entity.company_name = row['company_name']
                document_entity.company_id = row['company_id']
                document_entity.year = row['year']
                document_list.append(document_entity)
            cursor.close()
        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

        return document_list

    def get_exp_mitigation_lists(self, document_id):

        mitigation_keyword_list = []
        sql = 'select document_id, key_word_hit_id, key_word,locations from t_key_word_hits where  dictionary_type = 1002 and document_id = %s  order by key_word_hit_id'

        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sql, (document_id,))
            rows = cursor.fetchall()
            for row in rows:
                keyword_loc_entity = KeyWordLocationsEntity()
                keyword_loc_entity.key_word_hit_id = row['key_word_hit_id']
                keyword_loc_entity.key_word = row['key_word']
                keyword_loc_entity.locations = row['locations']
                mitigation_keyword_list.append(keyword_loc_entity)
            cursor.close()

        # print("Record inserted successfully!")

        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

        exp_keyword_list = []
        sql = 'select document_id, key_word_hit_id, key_word,locations,exposure_path_id from t_key_word_hits where dictionary_type = 1000 and document_id = %s order by key_word_hit_id'
        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sql, ((document_id,)))
            rows = cursor.fetchall()
            for row in rows:

                keyword_loc_entity = KeyWordLocationsEntity()
                keyword_loc_entity.key_word_hit_id = row['key_word_hit_id']
                keyword_loc_entity.key_word = row['key_word']
                keyword_loc_entity.locations = row['locations']
                keyword_loc_entity.exposure_path_id = row['exposure_path_id']
                exp_keyword_list.append(keyword_loc_entity)
            cursor.close()

        # print("Record inserted successfully!")

        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

        exp_insight_list = []
        sql = 'select key_word_hit_id1, key_word_hit_id2, key_word1, key_word2,exposure_path_id from t_exposure_pathway_insights where document_id = %s and score_normalized > %s'
        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sql, ((document_id, INSIGHT_SCORE_THRESHOLD)))
            rows = cursor.fetchall()
            for row in rows:

                insight_entity = Insight()
                insight_entity.keyword_hit_id1 = row['key_word_hit_id1']
                insight_entity.keyword_hit_id2 = row['key_word_hit_id2']
                insight_entity.keyword1 = row['key_word1']
                insight_entity.keyword2 = row['key_word2']
                insight_entity.exposure_path_id = row['exposure_path_id']
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
            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("select doc.document_id, comp.company_id, doc.document_name, doc.company_name, doc.year \
                                from t_document doc, t_sec_company comp \
                                where \
                                doc.mitigation_int_insights_generated = 0 and doc.company_name = comp.conformed_name\
                            and doc.int_insights_generated_ind = 1 and doc.mitigation_search_completed_ind = 1\
                            ")
            rows = cursor.fetchall()
            for row in rows:
                document_entity = DocumentEntity()
                document_entity.document_id = row['document_id']
                document_entity.document_name = row['document_name']
                document_entity.company_name = row['company_name']
                document_entity.company_id = row['company_id']
                document_entity.year = row['year']
                document_list.append(document_entity)

            cursor.close()
        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

        return document_list

    def get_int_mitigation_lists(self, document_id):

        mitigation_keyword_list = []
        sql = 'select document_id, key_word_hit_id, key_word,locations from t_key_word_hits where  dictionary_type = 1002 and document_id = %s  order by key_word_hit_id'

        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sql, ((document_id,)))
            rows = cursor.fetchall()
            for row in rows:

                keyword_loc_entity = KeyWordLocationsEntity()
                keyword_loc_entity.key_word_hit_id = row['key_word_hit_id']
                keyword_loc_entity.key_word = row['key_word']
                keyword_loc_entity.locations = row['locations']
                mitigation_keyword_list.append(keyword_loc_entity)

            cursor.close()

        # print("Record inserted successfully!")

        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

        int_keyword_list = []
        sql = 'select document_id, key_word_hit_id, key_word,locations,internalization_id from t_key_word_hits where dictionary_type = 1001 and document_id = %s order by key_word_hit_id'
        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sql, ((document_id,)))
            rows = cursor.fetchall()
            for row in rows:
                keyword_loc_entity = KeyWordLocationsEntity()
                keyword_loc_entity.key_word_hit_id = row['key_word_hit_id']
                keyword_loc_entity.key_word = row['key_word']
                keyword_loc_entity.locations = row['locations']
                keyword_loc_entity.intenalization_id = row['internalization_id']
                int_keyword_list.append(keyword_loc_entity)

            cursor.close()

        # print("Record inserted successfully!")

        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

        int_insight_list = []
        sql = 'select key_word_hit_id1, key_word_hit_id2, key_word1, key_word2,internalization_id from t_internalization_insights where document_id = %s and score_normalized > %s'
        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sql, ((document_id, INSIGHT_SCORE_THRESHOLD)))
            rows = cursor.fetchall()
            for row in rows:
                insight_entity = Insight()
                insight_entity = Insight()
                insight_entity.keyword_hit_id1 = row['key_word_hit_id1']
                insight_entity.keyword_hit_id2 = row['key_word_hit_id2']
                insight_entity.keyword1 = row['key_word1']
                insight_entity.keyword2 = row['key_word2']
                insight_entity.internalization_id = row['internalization_id']
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
            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("select doc.document_id, comp.company_id, doc.document_name, doc.company_name, doc.year \
                                from t_document doc, t_sec_company comp \
                                where \
                                doc.int_exp_insights_generated = 0 and doc.company_name = comp.conformed_name\
                                and doc.exp_insights_generated_ind = 1 and doc.int_insights_generated_ind = 1\
                            ")
            rows = cursor.fetchall()
            for row in rows:
                document_entity = DocumentEntity()
                document_entity.document_id = row['document_id']
                document_entity.document_name = row['document_name']
                document_entity.company_name = row['company_name']
                document_entity.company_id = row['company_id']
                document_entity.year = row['year']
                document_list.append(document_entity)
            cursor.close()
        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

        return document_list

    def get_exp_int_lists(self, document_id):

        exp_insight_location_list = []
        # sql = 'select document_id, key_word_hit_id, key_word,locations from t_key_word_hits where dictionary_type = 1000 and document_id = %s'

        sql = f"select exp.key_word_hit_id1, exp.key_word_hit_id2, exp.key_word1, exp.key_word2, hits.locations locationlist1, hits2.locations locationlist2 , exp.exposure_path_id\
                 from t_exposure_pathway_insights exp inner join  t_key_word_hits hits on hits.key_word_hit_id = exp.key_word_hit_id1 \
                                             inner join   t_key_word_hits hits2 on hits2.key_word_hit_id = exp.key_word_hit_id2 \
                where exp.document_id = %s and score_normalized > %s"

        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sql, ((document_id, INSIGHT_SCORE_THRESHOLD)))
            rows = cursor.fetchall()
            for row in rows:
                insight_entity = Insight()
                insight_entity.keyword_hit_id1 = row['key_word_hit_id1']
                insight_entity.keyword_hit_id2 = row['key_word_hit_id2']
                insight_entity.keyword1 = row['key_word1']
                insight_entity.keyword2 = row['key_word2']
                insight_entity.locations1 = row['locationlist1']
                insight_entity.locations2 = row['locationlist2']
                insight_entity.exposure_path_id = row['exposure_path_id']
                exp_insight_location_list.append(insight_entity)
            cursor.close()

        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

        int_insight_location_list = []

        sql = f"select int.key_word_hit_id1, int.key_word_hit_id2, int.key_word1, int.key_word2, hits.locations locationlist1, hits2.locations locationlist2, int.internalization_id\
                from t_internalization_insights int inner join  t_key_word_hits hits on hits.key_word_hit_id = int.key_word_hit_id1 \
                                     inner join   t_key_word_hits hits2 on hits2.key_word_hit_id = int.key_word_hit_id2      \
                where int.document_id = %s and score_normalized > %s "

        try:
            # Execute the SQL query
            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sql, ((document_id, INSIGHT_SCORE_THRESHOLD)))
            rows = cursor.fetchall()
            for row in rows:
                insight_entity = Insight()
                insight_entity.keyword_hit_id1 = row['key_word_hit_id1']
                insight_entity.keyword_hit_id2 = row['key_word_hit_id2']
                insight_entity.keyword1 = row['key_word1']
                insight_entity.keyword2 = row['key_word2']
                insight_entity.locations1 = row['locationlist1']
                insight_entity.locations2 = row['locationlist2']
                insight_entity.internalization_id = row['internalization_id']
                int_insight_location_list.append(insight_entity)
            cursor.close()

        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

        return exp_insight_location_list, int_insight_location_list

## CHANGES IN PROGRESS BELOW THIS LINE ##
    def save_Exp_Int_Insights(self, insightList, dictionary_type, document_id):
        """
        OPTIMIZED: Bulk insert for Exposure-Internalization insights using executemany
        Target: 500+ records/second (20x improvement)
        """
        if not insightList:
            if DB_LOGGING_ENABLED:
                self.log_generator.log_details("No insights to save")
            return

        start_time = time.time()
        sector_id = self.get_sector_id(document_id)

        # OPTIMIZATION 1: Pre-validate and batch convert data
        prep_start = time.time()
        insert_data = []
        skipped_records = 0

        if DB_LOGGING_ENABLED:
            self.log_generator.log_details(
                f"🔄 Starting OPTIMIZED save_Exp_Int_Insights for {len(insightList)} records...")

        for exp_int_insight_entity in insightList:
            # Quick validation first
            if (exp_int_insight_entity.document_id is None or
                    exp_int_insight_entity.document_name is None):
                skipped_records += 1
                if DB_LOGGING_ENABLED:
                    self.log_generator.log_details(
                        f"Skipping insight with missing required fields")
                continue

            # Batch convert all fields at once
            try:
                converted_row = (
                    self.convert_numpy_types(
                        exp_int_insight_entity.document_id),
                    self.convert_numpy_types(sector_id),
                    self.convert_numpy_types(
                        exp_int_insight_entity.document_name),
                    self.convert_numpy_types(
                        exp_int_insight_entity.exp_keyword_hit_id1),
                    self.convert_numpy_types(
                        exp_int_insight_entity.exp_keyword1),
                    self.convert_numpy_types(
                        exp_int_insight_entity.exp_keyword_hit_id2),
                    self.convert_numpy_types(
                        exp_int_insight_entity.exp_keyword2),
                    self.convert_numpy_types(
                        exp_int_insight_entity.int_key_word_hit_id1),
                    self.convert_numpy_types(
                        exp_int_insight_entity.int_key_word1),
                    self.convert_numpy_types(
                        exp_int_insight_entity.int_key_word_hit_id2),
                    self.convert_numpy_types(
                        exp_int_insight_entity.int_key_word2),
                    self.convert_numpy_types(exp_int_insight_entity.factor1),
                    self.convert_numpy_types(exp_int_insight_entity.factor2),
                    self.convert_numpy_types(exp_int_insight_entity.score),
                    self.convert_numpy_types(
                        exp_int_insight_entity.exposure_path_id),
                    self.convert_numpy_types(
                        exp_int_insight_entity.internalization_id),
                    self.convert_numpy_types(exp_int_insight_entity.year),
                    'Mohan Hanumantha',  # added_by
                    'Mohan Hanumantha'   # modify_by
                )

                # Final validation after conversion
                if converted_row[0] is not None and converted_row[2] is not None:
                    insert_data.append(converted_row)
                else:
                    skipped_records += 1
                    if DB_LOGGING_ENABLED:
                        self.log_generator.log_details(
                            f"Skipping insight with None values after conversion")

            except Exception as e:
                skipped_records += 1
                if DB_LOGGING_ENABLED:
                    self.log_generator.log_details(
                        f"Conversion error for record: {str(e)}")
                continue

        prep_time = time.time() - prep_start

        if not insert_data:
            if DB_LOGGING_ENABLED:
                self.log_generator.log_details(
                    "No valid insights to insert after validation")
            return

        # OPTIMIZATION 2: Use executemany for bulk insert
        bulk_start = time.time()
        sql = """INSERT INTO t_exp_int_insights(
                    document_id, sector_id, document_name, 
                    exp_keyword_hit_id1, exp_keyword1, exp_keyword_hit_id2, exp_keyword2,
                    int_key_word_hit_id1, int_key_word1, int_key_word_hit_id2, int_key_word2,
                    factor1, factor2, score, exposure_path_id, internalization_id, year,
                    added_dt, added_by, modify_dt, modify_by
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    CURRENT_TIMESTAMP, %s, CURRENT_TIMESTAMP, %s
                )"""

        try:
            # OPTIMIZATION 3: Single cursor with explicit transaction control
            cursor = self.dbConnection.cursor()

            # OPTIMIZATION 4: Use executemany for reliable bulk insert
            cursor.executemany(sql, insert_data)

            # OPTIMIZATION 5: Single commit at the end
            self.dbConnection.commit()
            cursor.close()

            bulk_time = time.time() - bulk_start
            total_time = time.time() - start_time

            # Enhanced telemetry
            if DB_LOGGING_ENABLED:
                self.log_generator.log_details(
                    f"✅ OPTIMIZED bulk insert completed:")
                self.log_generator.log_details(
                    f"   📝 Records processed: {len(insightList)}")
                self.log_generator.log_details(
                    f"   ✅ Records inserted: {len(insert_data)}")
                self.log_generator.log_details(
                    f"   ⚠️  Records skipped: {skipped_records}")
                self.log_generator.log_details(
                    f"   🔧 Preparation time: {prep_time:.3f}s ({prep_time/total_time*100:.1f}%)")
                self.log_generator.log_details(
                    f"   💾 Bulk insert time: {bulk_time:.3f}s ({bulk_time/total_time*100:.1f}%)")
                self.log_generator.log_details(
                    f"   ⏱️  Total time: {total_time:.3f}s")
                if bulk_time > 0:
                    self.log_generator.log_details(
                        f"   📈 Insertion rate: {len(insert_data)/bulk_time:.2f} records/sec")
                    self.log_generator.log_details(
                        f"   📊 Avg time/record: {bulk_time/len(insert_data)*1000:.2f}ms")

                # Performance rating
                records_per_sec = len(insert_data) / \
                    bulk_time if bulk_time > 0 else 0
                if records_per_sec >= 1000:
                    rating = "⚡ Excellent (1000+ records/sec)"
                elif records_per_sec >= 500:
                    rating = "🚀 Very Good (500-1000 records/sec)"
                elif records_per_sec >= 100:
                    rating = "✅ Good (100-500 records/sec)"
                elif records_per_sec >= 50:
                    rating = "⚠️  Fair (50-100 records/sec)"
                else:
                    rating = "🐌 Needs Optimization (<50 records/sec)"

                self.log_generator.log_details(
                    f"   🎯 Performance Rating: {rating}")
                self.log_generator.log_details(
                    '################################################################################################')

        except Exception as exc:
            self.dbConnection.rollback()
            if DB_LOGGING_ENABLED:
                self.log_generator.log_details(
                    f"❌ Error in optimized bulk insert EXP-INT insights: {str(exc)}")
            raise exc
## CHANGES IN PROGRESS ABOVE THIS LINE ##

    def get_mitigation_exp_int_document_list(self):
        document_list = []
        try:
            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("select doc.document_id, comp.company_id, doc.document_name, doc.company_name, doc.year \
                                from t_document doc, t_sec_company comp \
                                where \
                                doc.mitigation_int_exp_insights_generated = 0 and doc.company_name = comp.conformed_name\
                            and doc.exp_insights_generated_ind=1 and doc.int_insights_generated_ind=1 and doc.mitigation_search_completed_ind = 1\
                           ")
            rows = cursor.fetchall()
            for row in rows:
                document_entity = DocumentEntity()
                document_entity.document_id = row['document_id']
                document_entity.document_name = row['document_name']
                document_entity.company_name = row['company_name']
                document_entity.company_id = row['company_id']
                document_entity.year = row['year']
                document_list.append(document_entity)
            cursor.close()
        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

        return document_list

    def get_mitigation_exp_int_lists(self, document_id, year):

        mitigation_keyword_list = []
        sql = 'select document_id, key_word_hit_id, key_word,locations from t_key_word_hits where insights_generated = 0 and dictionary_type = 1002 and document_id = %s  order by key_word_hit_id'

        # sql = 'select document_id, key_word_hit_id, key_word,locations from t_key_word_hits where  insights_generated = 0 and \
        #         dictionary_type = 1002 and document_id = %s  and  dictionary_id = 1009 and key_word_hit_id = 1585'

        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sql, (document_id,))
            rows = cursor.fetchall()
            for row in rows:

                keyword_loc_entity = KeyWordLocationsEntity()
                keyword_loc_entity.key_word_hit_id = row['key_word_hit_id']
                keyword_loc_entity.key_word = row['key_word']
                keyword_loc_entity.locations = row['locations']
                mitigation_keyword_list.append(keyword_loc_entity)

            cursor.close()

            # print("Record inserted successfully!")

        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

        exp_int_insight_location_list = []
        sector_id = self.get_sector_id(document_id)
        # sql = 'select document_id, key_word_hit_id, key_word,locations from t_key_word_hits where dictionary_type = 1000 and document_id = %s'

        sql = """SELECT expint.unique_key,expint.document_id, expint.document_name, expint.exp_keyword_hit_id1,expint.exp_keyword1,expint.exp_keyword_hit_id2,expint.exp_keyword2,\
                expint.int_key_word_hit_id1,expint.int_key_word1, int_key_word_hit_id2,expint.int_key_word2,expint.factor1,expint.factor2,expint.score,expint.score_normalized, expint.exposure_path_id,expint.internalization_id,\
                exp1_hits.locations as exp1_locations, exp2_hits.locations as exp2_locations, int1_hits.locations as int1_locations, int2_hits.locations as int2_locations\
               from t_exp_int_insights expint \
                      INNER JOIN t_key_word_hits exp1_hits on exp1_hits.key_word_hit_id = expint.exp_keyword_hit_id1\
                      INNER JOIN t_key_word_hits exp2_hits on exp2_hits.key_word_hit_id = expint.exp_keyword_hit_id2\
                      INNER JOIN  t_key_word_hits int1_hits on int1_hits.key_word_hit_id = expint.int_key_word_hit_id1\
                      INNER JOIN  t_key_word_hits int2_hits on int2_hits.key_word_hit_id = expint.int_key_word_hit_id2\
                where expint.year = %s and expint.document_id = %s and expint.score_normalized > %s"""

        # DATE:Jun 10, 2025 - Filtering will not work if Sector Scores are not yet calculated
        # and expint.exposure_path_id in (\
        #                         select  top 10 exposure_path_id\
        #                         from t_sector_exp_insights where year= %s and sector_id=%s order by score_normalized DESC)"

        try:
            # Execute the SQL query

            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(
                sql, (year, document_id, EXP_INT_MITIGATION_THRESHOLD))
            # cursor.execute(sql, ((year, document_id, year,sector_id)))
            rows = cursor.fetchall()
            for row in rows:
                insight_entity = MitigationExpIntInsight()
                insight_entity.document_id = row['document_id']
                insight_entity.exp_keyword_hit_id1 = row['exp_keyword_hit_id1']
                insight_entity.exp_keyword1 = row['exp_keyword1']
                insight_entity.exp_keyword_hit_id2 = row['exp_keyword_hit_id2']
                insight_entity.exp_keyword2 = row['exp_keyword2']
                insight_entity.int_key_word_hit_id1 = row['int_key_word_hit_id1']
                insight_entity.int_key_word1 = row['int_key_word1']
                insight_entity.int_key_word_hit_id2 = row['int_key_word_hit_id2']
                insight_entity.int_key_word2 = row['int_key_word2']
                insight_entity.document_name = row['document_name']
                insight_entity.document_id = document_id
                insight_entity.internalization_id = row['internalization_id']
                insight_entity.exposure_path_id = row['exposure_path_id']
                insight_entity.exp1_locations = row['exp1_locations']
                insight_entity.exp2_locations = row['exp2_locations']
                insight_entity.int1_locations = row['int1_locations']
                insight_entity.int2_locations = row['int2_locations']
                exp_int_insight_location_list.append(insight_entity)
            cursor.close()

        except Exception as exc:
            print('Failing Here in get_mitigation_exp_int_lists')
            print(f"Error: {str(exc)}")
            raise exc

        return exp_int_insight_location_list, mitigation_keyword_list

    def save_Mitigation_Exp_Int_Insights(self, insightList, dictionary_type, document_id):
        mitigation_exp_int_insight_entity: MitigationExpIntInsight
        self.d_next_seed = 0
        sector_id = self.get_sector_id(document_id)

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
            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            # Construct the INSERT INTO statement

            # int_unique_key = self.get_next_surrogate_key(
            #     Lookups().Mitigation_Exp_INT_Insight_Type)
            sql = f"INSERT INTO t_mitigation_exp_int_insights( \
                        document_id , sector_id,document_name ,exp_keyword_hit_id1 ,exp_keyword1,exp_keyword_hit_id2 ,exp_keyword2 \
                        ,int_key_word_hit_id1,int_key_word1,int_key_word_hit_id2, int_key_word2 ,factor1 ,factor2 ,score, exposure_path_id, internalization_id\
                        ,mitigation_keyword_hit_id,mitigation_keyword\
                        ,added_dt,added_by ,modify_dt,modify_by,year\
                )\
                    VALUES\
                    ({document_id},{sector_id},N'{document_name}',{exp_keyword_hit_id1},N'{exp_keyword1}',{exp_keyword_hit_id2},N'{exp_keyword2}'\
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
        # Return mock data if database is disabled
        if self.database_disabled or self.dbConnection is None:
            print("⚠️  Database disabled - returning mock sector list")
            return ['Technology', 'Healthcare', 'Finance', 'Energy', 'Manufacturing']

        sector_list = []

        sql = 'select l.data_lookups_id sector_id, l.data_lookups_description  sector from t_data_lookups l where data_lookups_group_id = 5 order by l.data_lookups_description'

        try:
            # Execute the SQL query
            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row in rows:
                # Access by index for PostgreSQL - sector is the second column
                sector_list.append(row['sector'])
            cursor.close()

        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

        return sector_list

    def get_year_list(self):
        # Return mock data if database is disabled
        if self.database_disabled or self.dbConnection is None:
            print("⚠️  Database disabled - returning mock year list")
            return [2024, 2023, 2022, 2021, 2020]

        year_list = []

        sql = 'select distinct year from t_document order by year desc'

        try:
            # Execute the SQL query
            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row in rows:
                # Access by index for PostgreSQL - year is the first column
                year_list.append(row['year'])

        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

        return year_list

    def get_sector_id_year_list(self, sector_data_update=False, top10_chart_refeshed_ind=False, triangulation_data_refreshed_ind=False, yoy_chart_ind=False):
        sector_year_list = []
        sector_list = []

        if (sector_data_update):
            sql = 'select sector_id, year from t_sector_year_processing where sector_data_processed_ind = 0'
        elif (top10_chart_refeshed_ind):
            sql = 'select  secyr.sector_id,  secyr.year, map.company_name from t_sector_year_processing secyr\
                    inner join t_sec_company_sector_map map on map.sector_id = secyr.sector_id\
                    where secyr.top10_chart_refeshed_ind = 0'
        elif (triangulation_data_refreshed_ind):
            sql = 'select  secyr.sector_id,  secyr.year, map.company_name from t_sector_year_processing secyr\
                    inner join t_sec_company_sector_map map on map.sector_id = secyr.sector_id\
                    where secyr.triangulation_chart_refeshed_ind = 0'
        elif (yoy_chart_ind):
            sql = 'select  secyr.sector_id,  secyr.year, map.company_name from t_sector_year_processing secyr\
                    inner join t_sec_company_sector_map map on map.sector_id = secyr.sector_id\
                    where secyr.yoy_chart_refreshed_ind = 0'
        try:
            # Execute the SQL query
            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row in rows:
                if (top10_chart_refeshed_ind):
                    sector_year_list.append(SectorYearDBEntity(
                        SectorId=row['sector_id'], Year=row['year'], Company_Name=row['company_name']))
                elif (triangulation_data_refreshed_ind):
                    sector_year_list.append(SectorYearDBEntity(
                        SectorId=row['sector_id'], Year=row['year'], Company_Name=row['company_name']))
                elif (yoy_chart_ind):
                    sector_year_list.append(SectorYearDBEntity(
                        SectorId=row['sector_id'], Year=row['year'], Company_Name=row['company_name']))
                elif (sector_data_update):
                    sector_year_list.append(SectorYearDBEntity(
                        SectorId=row['sector_id'], Year=row['year'], Company_Name='N/A'))

            cursor.close()

        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

        return sector_year_list

    def get_company_list(self):
        company_list = []

        sql = 'select distinct company_name from t_sec_company_sector_map order by company_name'

        try:
            # Execute the SQL query
            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row in rows:
                # Access by index for PostgreSQL - company_name is the first column
                company_list.append(row['company_name'])
            cursor.close()

        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

        return company_list

    def get_doc_type_list(self):
        doc_type_list = []

        sql = 'select data_lookups_description doc_type from t_data_lookups where data_lookups_group_id = 1'

        try:
            # Execute the SQL query
            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row in rows:
                # Access by index for PostgreSQL - doc_type is the first column
                doc_type_list.append(row['doc_type'])
            cursor.close()

        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

        return doc_type_list

    def update_sector_stats(self, sector, year, generate_exp_sector_insights: bool, generate_int_sector_insights: bool, generate_exp_mit_sector_insights: bool, generate_exp_int_mit_sector_insights: bool, update_all: bool):
        sector_year_list = []
        if (update_all):
            sector_year_list = self.get_sector_id_year_list(
                sector_data_update=True)
        else:

            print('Sector Selected: '+sector)
            sector_id_sql = 'select lookups.data_lookups_id from t_data_lookups lookups where data_lookups_description = %s'
            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sector_id_sql, (((sector,))))

            sector_id = cursor.fetchone()['data_lookups_id']
            sector_year_list.append(SectorYearDBEntity(
                SectorId=sector_id, Year=year))
            cursor.close()

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

            sql_update = 'update t_sector_year_processing set  sector_data_processed_ind = 1 where sector_id = %s and year = %s'
            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(
                sql_update, ((sector_year.SectorId, sector_year.Year)))
            self.dbConnection.commit()
            cursor.close()

            print('Sector Stats Update Completed')

    def update_sector_exposure_stats(self, sector_id, year):
        print('Updating Exposure STATS for Sector:' +
              str(sector_id)+', Year:'+str(year))

        # sector_id_sql = 'select lookups.data_lookups_id from t_data_lookups lookups where data_lookups_description = %s'
        # cursor = self.dbConnection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        # cursor.execute(sector_id_sql, ((sector,)))
        # sector_id = cursor.fetchone()[0]

        # Exposure Pathway Sector STATS
        sql_update = 'update t_exposure_pathway_insights\
                      set score_normalized_sector = (score * 100)/(select max(score) from t_exposure_pathway_insights where sector_id = %s and year =%s)\
                         ,modify_dt = CURRENT_TIMESTAMP\
                      where sector_id = %s and year = %s'
        cursor = self.dbConnection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(sql_update, (((sector_id, year, sector_id, year))))
        self.dbConnection.commit()
        cursor.close()

        sql_delete = 'delete from  t_sector_exp_insights where sector_id =%s and year = %s'
        cursor = self.dbConnection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(sql_delete, ((sector_id, year)))
        self.dbConnection.commit()
        cursor.close()

        sql_insert = 'INSERT into t_sector_exp_insights(sector_id,year,esg_category_name,exposure_path_id,exposure_path_name,cluster_count_all,cluster_count,score,score_normalized,added_dt,added_by,modify_dt,modify_by)\
                    SELECT \
                        insights.sector_id,insights.year,  esg.esg_category_name ESG_Category,insights.exposure_path_id exposure_path_id,   exp.exposure_path_name Exposure_Pathway,\
                        count(*) Pathways, NULL, avg(insights.score) Score,  NULL, CURRENT_TIMESTAMP, %s,CURRENT_TIMESTAMP, %s\
                    FROM t_exposure_pathway_insights insights \
                            inner join t_exposure_pathway exp on exp.exposure_path_id = insights.exposure_path_id \
                            inner join t_impact_category imp on exp.impact_category_id = imp.impact_category_id\
                            inner join t_esg_category esg on imp.esg_category_id = esg.esg_category_id\
                    WHERE insights.year = %s and insights.sector_id = %s\
                    GROUP BY insights.sector_id,insights.year,  esg.esg_category_name , insights.exposure_path_id, exp.exposure_path_name'

        cursor = self.dbConnection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(sql_insert, (('MOHAN HANUMANTHA',
                                     'MOHAN HANUMANTHA', year, sector_id)))
        self.dbConnection.commit()
        cursor.close()

        sql_update_cluster = 'update t_sector_exp_insights set cluster_count = cluster_count_all/(select count(document_id) from t_document doc inner join t_sec_company_sector_map map on doc.company_name = map.company_name where map.sector_id = %s and  doc.year = %s)\
                               ,modify_dt = CURRENT_TIMESTAMP\
                             where  sector_id = %s and year = %s'

        cursor = self.dbConnection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(sql_update_cluster,
                       ((sector_id, year, sector_id, year)))
        self.dbConnection.commit()
        cursor.close()

        sql_update_normalize_score = 'update t_sector_exp_insights\
                                   set score_normalized = (score * 100)/(select max(score) from t_sector_exp_insights where sector_id = %s and year =%s)\
                                       ,modify_dt = CURRENT_TIMESTAMP\
                                   where sector_id = %s and year = %s'
        cursor = self.dbConnection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(sql_update_normalize_score,
                       ((sector_id, year, sector_id, year)))
        self.dbConnection.commit()
        cursor.close()

    def update_sector_exposure_internalization_stats(self, sector_id, year):
        print('Updating Internalization STATS for Sector:' +
              str(sector_id)+', Year:'+str(year))

        sql_delete = 'delete from  t_sector_exp_int_insights where sector_id =%s and year = %s'
        cursor = self.dbConnection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(sql_delete, (((sector_id, year))))
        self.dbConnection.commit()
        cursor.close()

        # print('Inserting Aggregate Data')
        sql_insert = 'INSERT into t_sector_exp_int_insights(sector_id,year,esg_category_name,exposure_path_id,exposure_path_name,internalization_name,cluster_count_all,score,score_normalized,added_dt,added_by,modify_dt,modify_by)\
                    SELECT\
                            insights.sector_id,insights.year,  esg.esg_category_name ESG_Category, insights.exposure_path_id exposure_path_id,  exp.exposure_path_name Exposure_Pathway,int.internalization_name,\
                            count(*) Pathways, avg(insights.score) Score , NULL, CURRENT_TIMESTAMP, %s,CURRENT_TIMESTAMP, %s\
                FROM t_exp_int_insights insights \
                        inner join t_exposure_pathway exp on exp.exposure_path_id = insights.exposure_path_id\
                        inner join t_internalization int on int.internalization_id = insights.internalization_id\
                        inner join t_impact_category imp on exp.impact_category_id = imp.impact_category_id\
                        inner join t_esg_category esg on imp.esg_category_id = esg.esg_category_id\
                WHERE insights.year = %s and insights.sector_id = %s\
                GROUP BY insights.sector_id,insights.year,  esg.esg_category_name , insights.exposure_path_id, exp.exposure_path_name, int.internalization_name'

        cursor = self.dbConnection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(sql_insert, (('MOHAN HANUMANTHA',
                                     'MOHAN HANUMANTHA', year, sector_id)))
        self.dbConnection.commit()
        cursor.close()

        # Update Cluster Count
        print('updating cluster count')
        sql_update_cluster = 'update t_sector_exp_int_insights set cluster_count = cluster_count_all/(select count(document_id) from t_document doc inner join t_sec_company_sector_map map on doc.company_name = map.company_name where map.sector_id = %s and  doc.year = %s)\
                                   ,modify_dt = CURRENT_TIMESTAMP\
                              where  sector_id = %s and year = %s'

        cursor = self.dbConnection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(sql_update_cluster,
                       ((sector_id, year, sector_id, year)))
        self.dbConnection.commit()
        cursor.close()

        # Normalize Score
        # print('Normalizing Score')
        sql_update_normalize_score = 'update t_sector_exp_int_insights\
                                   set score_normalized = (score * 100)/(select max(score) from t_sector_exp_int_insights where sector_id = %s and year = %s)\
                                      ,modify_dt = CURRENT_TIMESTAMP\
                                   where sector_id = %s and year = %s'
        cursor = self.dbConnection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(sql_update_normalize_score,
                       ((sector_id, year, sector_id, year)))
        self.dbConnection.commit()
        cursor.close()

    def update_sector_exposure_int_mitigation_stats(self, sector_id, year):
        print('Updating Exposure->Internalization->Mitigation STATS for Sector:' +
              str(sector_id)+', Year:'+str(year))

        # # Exposure Internalization Pathway Sector STATS
        # sql_update = 'update t_mitigation_exp_int_insights\
        #               set score_normalized_sector = (score * 100)/(select max(score) from t_mitigation_exp_int_insights where sector_id = %s and year = %s)\
        #                        ,modify_dt = CURRENT_TIMESTAMP\
        #                     where sector_id = %s and year = %s'

        # cursor = self.dbConnection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        # cursor.execute(sql_update, ((sector_id, year, sector_id, year)))
        # self.dbConnection.commit()
        # cursor.close()

        sql_delete = 'delete from  t_sector_exp_int_mitigation_insights where sector_id = %s and year = %s'
        cursor = self.dbConnection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(sql_delete, ((sector_id, year)))
        self.dbConnection.commit()
        cursor.close()

        # print('Inserting Aggregate Data')
        sql_insert = 'INSERT into t_sector_exp_int_mitigation_insights(sector_id,year,esg_category_name,exposure_path_id,internalization_id,exposure_path_name,internalization_name,cluster_count_all,score,score_normalized,added_dt,added_by,modify_dt,modify_by)\
                      SELECT   insights.sector_id,insights.year,  esg.esg_category_name ESG_Category,insights.exposure_path_id exposure_path_id, insights.internalization_id, exp.exposure_path_name,int.internalization_name,\
                            count(*) Pathways, avg(insights.score) Score, NULL, CURRENT_TIMESTAMP, %s,CURRENT_TIMESTAMP, %s\
                    FROM t_mitigation_exp_int_insights insights\
                        INNER JOIN t_exposure_pathway exp on exp.exposure_path_id = insights.exposure_path_id\
                        INNER JOIN t_internalization int on int.internalization_id = insights.internalization_id  and int.exposure_path_id = insights.exposure_path_id\
                        inner join t_impact_category imp on exp.impact_category_id = imp.impact_category_id\
                        inner join t_esg_category esg on imp.esg_category_id = esg.esg_category_id\
                WHERE insights.year = %s and insights.sector_id = %s\
                GROUP by insights.sector_id,  insights.year,  esg.esg_category_name, insights.exposure_path_id, insights.internalization_id, exp.exposure_path_name,int.internalization_name'

        # Removed from FROM Clause. Add back to break down at Mitigation Level
        # INNER JOIN t_key_word_hits hits on insights.mitigation_keyword_hit_id = hits.key_word_hit_id\
        # INNER JOIN t_mitigation mit on hits.dictionary_id = mit.dictionary_id

        cursor = self.dbConnection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(sql_insert, (('MOHAN HANUMANTHA',
                                     'MOHAN HANUMANTHA', year, sector_id)))
        self.dbConnection.commit()
        cursor.close()

        # Update Cluster Count
        # print('updating cluster count')

        sql_update_cluster = 'update t_sector_exp_int_mitigation_insights \
                              set cluster_count = cluster_count_all/(select count(document_id) from t_document doc inner join t_sec_company_sector_map map on doc.company_name = map.company_name where map.sector_id = %s and  doc.year = %s)\
                                 ,modify_dt = CURRENT_TIMESTAMP\
                                where  sector_id = %s and year = %s'

        cursor = self.dbConnection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(sql_update_cluster,
                       ((sector_id, year, sector_id, year)))
        self.dbConnection.commit()
        cursor.close()

        # Normalize Score
        # print('Normalizing Score')

        sql_update_normalize_score = 'update t_sector_exp_int_mitigation_insights\
                                        set score_normalized = (score * 100)/(select max(score) from t_sector_exp_int_mitigation_insights where sector_id = %s and year = %s)\
                                        ,modify_dt = CURRENT_TIMESTAMP\
                                        where sector_id = %s and year = %s'
        cursor = self.dbConnection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(sql_update_normalize_score,
                       ((sector_id, year, sector_id, year)))
        self.dbConnection.commit()
        cursor.close()

    def update_sector_exposure__mitigation_stats(self, sector_id, year):
        print('Updating Exposure Mitigation STATS for Sector:' +
              str(sector_id)+', Year:'+str(year))

        # Exposure Internalization Pathway Sector STATS
        sql_update = 'update t_mitigation_exp_insights\
                      set score_normalized_sector = (score * 100)/(select max(score) from t_mitigation_exp_insights where sector_id = %s and year = %s)\
                         ,modify_dt = CURRENT_TIMESTAMP\
                      where sector_id = %s and year = %s'

        cursor = self.dbConnection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(sql_update, (sector_id, year, sector_id, year))
        self.dbConnection.commit()
        cursor.close()

        sql_delete = 'delete from  t_sector_exp_mitigation_insights where sector_id = %s and year = %s'
        cursor = self.dbConnection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(sql_delete, (sector_id, year))
        self.dbConnection.commit()
        cursor.close()

        sql_insert = 'INSERT into t_sector_exp_mitigation_insights(sector_id,year,esg_category_name,exposure_path_id,exposure_path_name,\
                             cluster_count_all,score,score_normalized,added_dt,added_by,modify_dt,modify_by)\
                    SELECT   insights.sector_id,insights.year,esg.esg_category_name,insights.exposure_path_id ,  exp.exposure_path_name ,\
                             count(*), avg(insights.score), NULL, CURRENT_TIMESTAMP, %s,CURRENT_TIMESTAMP, %s\
                    FROM t_mitigation_exp_insights insights\
                        INNER JOIN t_exposure_pathway exp on exp.exposure_path_id = insights.exposure_path_id\
                        inner join t_impact_category imp on exp.impact_category_id = imp.impact_category_id\
                        inner join t_esg_category esg on imp.esg_category_id = esg.esg_category_id\
                        INNER JOIN t_key_word_hits hits on insights.mitigation_keyword_hit_id = hits.key_word_hit_id\
                        INNER JOIN t_mitigation mit on hits.dictionary_id = mit.dictionary_id\
                WHERE insights.year = %s and insights.sector_id = %s\
                GROUP by insights.sector_id,  insights.year,  esg.esg_category_name, insights.exposure_path_id,exp.exposure_path_name'

        cursor = self.dbConnection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(sql_insert, ('MOHAN HANUMANTHA',
                                    'MOHAN HANUMANTHA', year, sector_id))
        self.dbConnection.commit()
        cursor.close()

        # Update Cluster Count
        # print('updating cluster count')
        sql_update_cluster = 'update t_sector_exp_mitigation_insights set cluster_count = cluster_count_all/(select count(document_id) from t_document doc inner join t_sec_company_sector_map map on doc.company_name = map.company_name where map.sector_id = %s and  doc.year = %s)\
                              ,modify_dt = CURRENT_TIMESTAMP\
                                where  sector_id = %s and year = %s'

        cursor = self.dbConnection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(sql_update_cluster,
                       (sector_id, year, sector_id, year))
        self.dbConnection.commit()
        cursor.close()

        # Normalize Score
        sql_update_normalize_score = 'update t_sector_exp_mitigation_insights\
                                   set score_normalized = (score * 100)/(select max(score) from t_sector_exp_mitigation_insights where sector_id = %s and year = %s)\
                                     ,modify_dt = CURRENT_TIMESTAMP\
                                    where sector_id = %s and year = %s'
        cursor = self.dbConnection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(sql_update_normalize_score,
                       (sector_id, year, sector_id, year))
        self.dbConnection.commit()
        cursor.close()

        # Build Reporting Tables

    def update_reporting_tables(self, sector, year, generate_exp_rpt_insights: bool, generate_int_rpt_insights: bool, generate_mit_rpt_insights: bool, update_all: bool, keywords_only=True):

        sector_id_sql = 'select lookups.data_lookups_id from t_data_lookups lookups where data_lookups_description = %s'
        cursor = self.dbConnection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(sector_id_sql, (sector,))
        sector_id = cursor.fetchone()['data_lookups_id']
        cursor.close()
        if (generate_exp_rpt_insights):
            self.update_exposure_reporting(
                sector_id=sector_id, year=year, update_all=update_all, keywords_only=keywords_only)

    def update_exposure_reporting(self, sector_id, year, update_all, keywords_only):
        if (update_all):
            if (not keywords_only):
                print('Update Exposure Report for All Sectors and years')

                sql_delete = 'truncate table t_rpt_exposure_pathway_insights'
                cursor = self.dbConnection.cursor(
                    cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute(sql_delete)
                self.dbConnection.commit()
                cursor.close()

                sql_insert = 'INSERT INTO t_rpt_exposure_pathway_insights( sector_id, ((company_name,year,document_id, content_type ,document_type,exposure_path_id, esg_category_name,exposure_path_name, cluster_count,score_normalized,\
                                unique_key_words,chat_gpt_text,added_dt,added_by,modify_dt,modify_by)))\
                                \
                                SELECT comp.sector_id, doc.company_name,doc.year,doc.document_id, doc.content_type,lookups.data_lookups_description Document_Type,exp.exposure_path_id,esg.esg_category_name,exp.exposure_path_name,\
                                        count(*), AVG(insights.score_normalized) , NULL,NULL,CURRENT_TIMESTAMP, %s, CURRENT_TIMESTAMP,%s\
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
                cursor = self.dbConnection.cursor(
                    cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute(sql_insert, ('Mohan Hanumantha',
                                            'Mohan Hanumantha'))
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

                sql_delete = 'delete from  t_rpt_exposure_pathway_insights where sector_id = %s and year = %s'
                cursor = self.dbConnection.cursor(
                    cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute(sql_delete, (sector_id, year))
                self.dbConnection.commit()
                cursor.close()
                sql_insert = 'INSERT INTO t_rpt_exposure_pathway_insights( sector_id,company_name,year,document_id, content_type ,document_type,exposure_path_id, esg_category_name,exposure_path_name, cluster_count,score,score_normalized,\
                            unique_key_words,chat_gpt_text,added_dt,added_by,modify_dt,modify_by)\
                            \
                            SELECT comp.sector_id, doc.company_name,doc.year,doc.document_id, doc.content_type,lookups.data_lookups_description Document_Type,exp.exposure_path_id,esg.esg_category_name,exp.exposure_path_name,\
                                    count(*), AVG(insights.score),NULL , NULL,NULL,CURRENT_TIMESTAMP, %s, CURRENT_TIMESTAMP, %s\
                            FROM t_exposure_pathway_insights insights\
                                    inner join t_exposure_pathway exp on exp.exposure_path_id = insights.exposure_path_id\
                                    inner join t_impact_category imp on exp.impact_category_id = imp.impact_category_id\
                                    inner join t_esg_category esg on imp.esg_category_id = esg.esg_category_id\
                                    inner join t_document doc on doc.document_id = insights.document_id and doc.year = %s\
                                    inner join t_data_lookups lookups on lookups.data_lookups_id = doc.content_type and lookups.data_lookups_group_id = 1\
                                    inner join t_sec_company_sector_map comp on doc.company_name = comp.company_name and  comp.sector_id = %s\
                            GROUP by comp.sector_id, doc.company_name,doc.year,doc.document_id,doc.content_type,lookups.data_lookups_description,esg.esg_category_name,exp.exposure_path_id,exp.exposure_path_name\
                            ORDER BY comp.sector_id, doc.company_name,doc.year,doc.document_id,doc.content_type,lookups.data_lookups_description,esg.esg_category_name,exp.exposure_path_id,exp.exposure_path_name\
                            '
                cursor = self.dbConnection.cursor(
                    cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute(sql_insert, ('Mohan Hanumantha',
                               'Mohan Hanumantha', year, sector_id))
                self.dbConnection.commit()
                cursor.close()

        # Normalize data
        print('Normalize Rpt Exposure Path Scores')
        sql = 'select distinct document_id from t_rpt_exposure_pathway_insights where score_normalized is null'
        try:
            # Execute the SQL query
            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row in rows:
                print(row['document_id'])
                sql_update = 'update t_rpt_exposure_pathway_insights set score_normalized = (score * 100)/(select max(score) from t_rpt_exposure_pathway_insights where document_id = %s) where document_id = %s'
                cursor.execute(
                    sql_update, (row['document_id'], row['document_id']))
                self.dbConnection.commit()
            cursor.close()
        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc
        print('Completed Normalizing Rpt Exposure Path Scores')

        # Chat GPT Support
        # self.update_exposure_rpt_unique_keywordlist(sector_id, year)

    def update_exposure_rpt_unique_keywordlist(self, sector_id, year):
        print('Updating Unique Keywords for sector id:' +
              str(sector_id)+'  Year:'+str(year))
        # Update Unique Keywords in the list

        rpt_exp_list = []

        exp_rpt_sql = 'select unique_key, document_id, exposure_path_id from t_rpt_exposure_pathway_insights where sector_id = %s and year = %s'

        try:
            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(exp_rpt_sql, (sector_id, year))
            rows = cursor.fetchall()
            for row in rows:
                rpt_exp_list.append(
                    Reporting_DB_Entity(
                        unique_key=row['unique_key'],
                        DocumentId=row['document_id'],
                        ExposurePathId=row['exposure_path_id'])
                )

        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

        cursor = self.dbConnection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)

        for exp_rpt_line_item in rpt_exp_list:
            unique_keyword_list = ''
            keyword_sql = 'select distinct key_word1 keyword from t_exposure_pathway_insights where exposure_path_id = %s and document_id = %s\
                            UNION\
                            select distinct key_word2 keyword from t_exposure_pathway_insights where exposure_path_id = %s and document_id = %s\
                            '
            cursor.execute(
                keyword_sql, (exp_rpt_line_item.ExposurePathId, exp_rpt_line_item.DocumentId, exp_rpt_line_item.ExposurePathId, exp_rpt_line_item.DocumentId))

            rows = cursor.fetchall()
            for row in rows:
                unique_keyword_list = unique_keyword_list + \
                    row['keyword'] + ','
            unique_keyword_list = unique_keyword_list.rstrip(',')
            sql_update = 'update t_rpt_exposure_pathway_insights set unique_key_words = %s where unique_key =%s'
            cursor.execute(sql_update, (unique_keyword_list,
                           exp_rpt_line_item.unique_key))
        self.dbConnection.commit()
        cursor.close()

        # Build Chart Tables

    def update_chart_tables(self, generate_top10_exposure_chart_data=False, generate_triangulation_data=False, generate_yoy_chart_data=False):
        if (generate_top10_exposure_chart_data):
            self.update_top10_chart_data()
        if (generate_triangulation_data):
            self.update_triangulation_chart_data()
        if (generate_yoy_chart_data):
            self.update_yoy_chart_data()

    def update_top10_chart_data(self):
        sector_year_list: SectorYearDBEntity = self.get_sector_id_year_list(
            top10_chart_refeshed_ind=True)
        print('Started Processing Top10 Exposure Chart Data')
        cursor = self.dbConnection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)

        for sector_year in sector_year_list:
            print('Company:'+sector_year.Company_Name + '  Sector ID:' +
                  str(sector_year.SectorId)+'  Year'+str(sector_year.Year))
            try:
                cursor.execute("sp_load_top10_exposure_data %s, (%s, %s", (sector_year.Company_Name,
                               sector_year.SectorId, sector_year.Year))
                self.dbConnection.commit()
                cursor.close()
            except Exception as exc:
                print(f"Error: {str(exc)}")
                raise exc

        for sector_year in sector_year_list:
            try:
                cursor.execute("update t_sector_year_processing set top10_chart_refeshed_ind = 1, ((modify_dt = CURRENT_TIMESTAMP ,modify_by = N'Mohan Hanumantha' where sector_id = %s and year = %s",
                               sector_year.SectorId, sector_year.Year)
                self.dbConnection.commit()
                cursor.close()
            except Exception as exc:
                print(f"Error: {str(exc)}")
                raise exc
        print('Completed Processing Top10 Exposure Chart Data')

    def update_triangulation_chart_data(self):

        sector_year_list: SectorYearDBEntity = self.get_sector_id_year_list(
            triangulation_data_refreshed_ind=True)
        print('Started Processing Triangulation Chart Data')
        cursor = self.dbConnection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)

        for sector_year in sector_year_list:
            print('Company:'+sector_year.Company_Name + '  Sector ID:' +
                  str(sector_year.SectorId)+'  Year'+str(sector_year.Year))
            try:
                cursor.execute("sp_load_triangulation_chart_data %s, (%s, %s", (sector_year.Company_Name,
                               sector_year.SectorId, sector_year.Year))
                self.dbConnection.commit()
                cursor
            except Exception as exc:
                print(f"Error: {str(exc)}")
                raise exc

        cursor = self.dbConnection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        for sector_year in sector_year_list:
            try:
                cursor.execute("update t_sector_year_processing set triangulation_chart_refeshed_ind = 1, ((modify_dt = CURRENT_TIMESTAMP ,modify_by = N'Mohan Hanumantha' where sector_id = %s and year = %s",
                               sector_year.SectorId, sector_year.Year)
                self.dbConnection.commit()
                cursor.close()

            except Exception as exc:
                print(f"Error: {str(exc)}")
                raise exc
            print('Completed Processing Triangulation Chart Data')

    def update_yoy_chart_data(self):

        sector_year_list: SectorYearDBEntity = self.get_sector_id_year_list(
            yoy_chart_ind=True)
        print('Started Processing YOY Chart Data')
        cursor = self.dbConnection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)

        for sector_year in sector_year_list:
            print('Company:'+sector_year.Company_Name + '  Sector ID:' +
                  str(sector_year.SectorId)+'  Year'+str(sector_year.Year))

            try:

                sql = 'delete from  t_chart_yoy where sector_id = %s and year = %s and company_name = %s'
                cursor.execute(sql, (sector_year.SectorId,
                               sector_year.Year, sector_year.Company_Name))

                sql = 'INSERT INTO t_chart_yoy(company_name, sector_id, year, exposure_path_name,exposure_score, exposure_score_normalized, added_dt, added_by,modify_dt, modify_by)\
                    SELECT  doc.company_name Company, insights.sector_id,insights.year, exp.exposure_path_name Exposure_Pathway,avg(insights.score) Score,  NULL, CURRENT_TIMESTAMP, %s,CURRENT_TIMESTAMP, %s\
                    FROM t_exposure_pathway_insights insights\
                        inner join t_exposure_pathway exp on exp.exposure_path_id = insights.exposure_path_id \
                        inner join t_impact_category imp on exp.impact_category_id = imp.impact_category_id\
                        inner join t_esg_category esg on imp.esg_category_id = esg.esg_category_id\
                        inner join t_document doc on doc.document_id = insights.document_id and doc.company_name = %s and doc.year = %s\
                GROUP BY  doc.company_name ,insights.sector_id,insights.year,  esg.esg_category_name , insights.exposure_path_id, exp.exposure_path_name\
                ORDER BY doc.company_name ,insights.sector_id,insights.year, Score desc'

                cursor.execute(sql, ('Mohan Hanumantha', 'Mohan Hanumantha',
                               sector_year.Company_Name, sector_year.Year))

                sql = 'update t_chart_yoy \
                      set exposure_score_normalized = (exposure_score * 100)/(select max(exposure_score) from t_chart_yoy where sector_id = %s and year = %s and company_name = %s)\
                      ,modify_dt = CURRENT_TIMESTAMP\
                       where sector_id = %s and year =%s and company_name = %s'

                cursor.execute(sql, (sector_year.SectorId,
                               sector_year.Year, sector_year.Company_Name, sector_year.SectorId,
                               sector_year.Year, sector_year.Company_Name))

                self.dbConnection.commit()
                cursor.close()

            except Exception as exc:
                print(f"Error: {str(exc)}")
                raise exc

        cursor = self.dbConnection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        for sector_year in sector_year_list:
            try:
                cursor.execute("update t_sector_year_processing set yoy_chart_refreshed_ind = 1, ((modify_dt = CURRENT_TIMESTAMP ,modify_by = N'Mohan Hanumantha' where sector_id = %s and year = %s",
                               sector_year.SectorId, sector_year.Year)
                self.dbConnection.commit()
                cursor.close()

            except Exception as exc:
                print(f"Error: {str(exc)}")
                raise exc
            print('Completed Processing YoY Chart Data')

    # TELEMETRICS LOGGING METHOD

    def _log_telemetrics(self, operation_name, total_records, total_time, preparation_time=0, db_operation_time=0, commit_time=0, additional_metrics=None):
        """
        Centralized telemetrics logging method

        Args:
            operation_name (str): Name of the operation being measured
            total_records (int): Total number of records processed
            total_time (float): Total time taken for the operation in seconds
            preparation_time (float): Time spent preparing data
            db_operation_time (float): Time spent on database operations
            commit_time (float): Time spent on commits
            additional_metrics (dict): Optional additional metrics to log
        """
        if not DB_LOGGING_ENABLED:
            return

        # Calculate percentages
        prep_percentage = (preparation_time / total_time *
                           100) if total_time > 0 else 0
        db_percentage = (db_operation_time / total_time *
                         100) if total_time > 0 else 0
        commit_percentage = (commit_time / total_time *
                             100) if total_time > 0 else 0

        # Calculate performance metrics
        records_per_second = total_records / total_time if total_time > 0 else 0
        avg_time_per_record = (
            total_time / total_records * 1000) if total_records > 0 else 0

        # Log telemetrics
        self.log_generator.log_details(f"📊 TELEMETRICS - {operation_name}:")
        self.log_generator.log_details(f"   📝 Total Records: {total_records}")
        self.log_generator.log_details(f"   ⏱️  Total Time: {total_time:.3f}s")

        if preparation_time > 0:
            self.log_generator.log_details(
                f"   🔧 Preparation Time: {preparation_time:.3f}s ({prep_percentage:.1f}%)")
        if db_operation_time > 0:
            self.log_generator.log_details(
                f"   💾 DB Operation Time: {db_operation_time:.3f}s ({db_percentage:.1f}%)")
        if commit_time > 0:
            self.log_generator.log_details(
                f"   ✅ Commit Time: {commit_time:.3f}s ({commit_percentage:.1f}%)")

        self.log_generator.log_details(
            f"   📈 Records/Second: {records_per_second:.2f}")
        self.log_generator.log_details(
            f"   📊 Avg Time/Record: {avg_time_per_record:.2f}ms")

        # Log any additional metrics
        if additional_metrics:
            for key, value in additional_metrics.items():
                self.log_generator.log_details(f"   📌 {key}: {value}")

        self.log_generator.log_details(
            f"   ✅ Operation completed successfully")
        self.log_generator.log_details(
            '################################################################################################')


# gen = InsightGeneratorDBManager("Development")
# gen.update_validation_completed_status()
