import pyodbc
import datetime as dt

class InsightGeneratorDBManager:

    def __init__(self) -> None:
        self.dbConnection = pyodbc.connect('DRIVER={ODBC Driver 18 for SQL Server};SERVER=earthdevdb.database.windows.net;UID=earthdevdbadmin@earthdevdb.database.windows.net;PWD=3q45yE3fEgQej8h!@;database=earth-dev')


    def get_dictionary_terms(self):
        pass

    def get_company_list(self,sic_code:str, company_name:str):
        
        sic_code = '%'+sic_code+'%'
        company_name = '%'+company_name+'%'

        sql = "SELECT sic.sic_code, sic.industry_title,header.conformed_name, header.form_type,header.document_id, header.document_name, header.reporting_year, header.reporting_quarter\
               FROM dbo.t_sic_codes sic INNER JOIN dbo.t_sec_document_header header ON sic.sic_code = header.sic_code_4_digit \
                    and header.reporting_year = 2022\
                    where sic.industry_title like ? and header.conformed_name like ? \
                    order by sic.sic_code"

        try:
            # Execute the SQL query
           cursor =self.dbConnection.cursor()
           cursor.execute(sql, sic_code, company_name)
           rows = cursor.fetchall()
           for row in rows:
                print(row.sic_code,' ', row.industry_title,row.conformed_name, row.form_type, row.document_id,row.document_name, row.reporting_year, row.reporting_quarter)
           cursor.close()

            # print("Record inserted successfully!")
        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc

    def save_insights(self):
        pass

    def remove_insights(self):
        pass



insightdbMgr =  InsightGeneratorDBManager()

insightdbMgr.get_company_list('Metal Mining','Lithium')