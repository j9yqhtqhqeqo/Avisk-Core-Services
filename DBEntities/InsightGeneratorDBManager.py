import sys
from pathlib import Path
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

import pyodbc
import datetime as dt
from DBEntities.DocumentHeaderEntity import DocHeaderEntity
from DBEntities.DictionaryEntity import DictionaryEntity


class InsightGeneratorDBManager:

    def __init__(self) -> None:
        self.dbConnection = pyodbc.connect(
            'DRIVER={ODBC Driver 18 for SQL Server};SERVER=earthdevdb.database.windows.net;UID=earthdevdbadmin@earthdevdb.database.windows.net;PWD=3q45yE3fEgQej8h!@;database=earth-dev')
        

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


    def get_exp_dictionary_term_list(self):

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