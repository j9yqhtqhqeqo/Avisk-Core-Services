import pyodbc
from DocumentProcessor import tenKProcessor
import datetime as dt
import re

class tenKDatabaseProcessor(tenKProcessor):

    def __init__(self) -> None:
        super().__init__()
        self.d_current_document_seed=0
        self.b_load_document_seed_from_db = True
        self.dbConnection = pyodbc.connect('DRIVER={ODBC Driver 18 for SQL Server};SERVER=earthdevdb.database.windows.net;UID=earthdevdbadmin@earthdevdb.database.windows.net;PWD=3q45yE3fEgQej8h!@;database=earth-dev')
        self.current_count:int
        
    def processDocumentHeader(self, current_count:0, last_batch = False):
        self.current_count = current_count
        self.b_last_batch = last_batch
        self.preProcessDocumentData()
        self.extractDocumentHeader()
        self.saveResults()
    

    def getCurrentDocumentSeed(self):
        if(self.b_load_document_seed_from_db):
            cursor = self.dbConnection.cursor()
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

    def getWellformedContent(self, orig_content):
        return orig_content.replace("'", "''")
 
    def saveResults(self):
        if(self.b_process_hader_only):
            try:
                if(self.b_bulk_mode):
                    self.saveDocumentHeaderBulk()
                else:
                    self.saveDocumentHeader()

            except (Exception) as exc:

                print(f'Error Processing File: = {self.f_input_file_path}\n')
                if self.f_failed_log:
                    f_log = open(self.f_failed_log, 'a')
                    f_log.write(f'{dt.datetime.now()}\n' +
                                f'Error Processing File: {self.f_input_file_path}\n')
                    f_log.write(f'Error Details:\n' + f'{exc.args}\n\n')
                    f_log.flush()
                raise exc
        else:
                try:
                    self.insertData()
                    return 1
                except (Exception) as exc:

                    print(f'Error Processing File: = {self.f_input_file_path}\n')
                    if self.f_failed_log:
                        f_log = open(self.f_failed_log, 'a')
                        f_log.write(f'{dt.datetime.now()}\n' +
                                    f'Error Processing File: {self.f_input_file_path}\n')
                        f_log.write(f'Error Details:\n' + f'{exc.args}\n\n')
                        f_log.flush()
                        raise exc           

    def saveDocumentHeader(self):
        
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
                ({self.d_current_document_seed},{self.d_reporting_year},{self.d_reporting_quarter},N'{self.f_document_name}',\
                N'{self.conformed_name}', N'{self.standard_industry_classification}', {self.irs_number} ,N'{self.state_of_incorporation}',\
                N'{self.fiscal_year_end}', N'{self.form_type}', N'{self.street_1}',N'{self.city}', N'{self.state}',N'{self.zip}',\
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

    def saveDocumentHeaderBulk(self):
        
        self.d_current_document_seed = self.getCurrentDocumentSeed()

        # Create a cursor object to execute SQL queries
        cursor = self.dbConnection.cursor()
        # Construct the INSERT INTO statement

        sic_code_4_digit_exp = re.search('\d+', self.standard_industry_classification)
        sic_code_4_digit = 0
        if(sic_code_4_digit_exp):
             sic_code_4_digit = int(sic_code_4_digit_exp.group())

        sql = f"INSERT INTO dbo.t_sec_document_header( \
            document_id ,  reporting_year, reporting_quarter, document_name,\
            conformed_name ,sic_code, sic_code_4_digit,irs_number, state_of_incorporation ,fiscal_year_end ,form_type,street_1,city ,state , zip,\
            added_dt,added_by ,modify_dt,modify_by\
            )\
                VALUES\
                ({self.d_current_document_seed},{self.d_reporting_year},{self.d_reporting_quarter},N'{self.f_document_name}',\
                N'{self.conformed_name}', N'{self.standard_industry_classification}',{sic_code_4_digit} ,{self.irs_number} ,N'{self.state_of_incorporation}',\
                N'{self.fiscal_year_end}', N'{self.form_type}', N'{self.street_1}',N'{self.city}', N'{self.state}',N'{self.zip}',\
                CURRENT_TIMESTAMP, N'Mohan Hanumantha',CURRENT_TIMESTAMP, N'Mohan Hanumantha')"
        try:
            # Execute the SQL query
            cursor.execute(sql)
            # print("Record inserted successfully!")
        except Exception as exc:
            # Rollback the transaction if any error occurs
            print(f"Error: {str(exc)}")
            raise exc
        
        if(self.current_count == 100 or self.b_last_batch):
            try:
                self.dbConnection.commit()
            except Exception as exc:
                # Rollback the transaction if any error occurs
                self.dbConnection.rollback()
                print(f"Error: {str(exc)}")
                raise exc
        # if(self.b_last_batch):
        #     try:
        #         cursor.close()
        #         self.dbConnection.close()
        #         print("Batch inserted successfully!")
        #     except Exception as exc:
        #         # Rollback the transaction if any error occurs
        #         self.dbConnection.rollback()
        #         print(f"Error: {str(exc)}")
        #         raise exc

    def CleanupDBConnection(self):
        if(self.b_last_batch):
            try:
                self.dbConnection.close()
                print("Batch Processing Complete!")
            except Exception as exc:
                # Rollback the transaction if any error occurs
                self.dbConnection.rollback()
                print(f"Error: {str(exc)}")
                raise exc

    def insertData(self):

        # Establish a connection to the SQL Server database
        conn = pyodbc.connect('DRIVER={ODBC Driver 18 for SQL Server};SERVER=earthdevdb.database.windows.net;UID=earthdevdbadmin@earthdevdb.database.windows.net;PWD=3q45yE3fEgQej8h!@;database=earth-dev')
    
        # Create a cursor object to execute SQL queries
        cursor = conn.cursor()
        conformedName ="TEST NAME"
        # Construct the INSERT INTO statement
        sql = f"INSERT INTO dbo.t_sec_document( \
            document_id , reporting_year, reporting_quarter, \
            conformed_name ,sic_code, irs_number, state_of_incorporation ,fiscal_year_end ,form_type,street_1,city ,state , zip,\
            form_item0 ,form_item1 ,form_item1A ,form_item1B ,form_item2 ,form_item3 ,form_item4 ,form_item5 ,form_item6 ,form_item7 ,form_item7A ,form_item8 ,\
            form_item9 ,form_item9A ,form_item9B ,form_item9C ,form_item10 ,form_item11 ,form_item12 ,form_item13 ,form_item14 ,form_item15 ,form_item16 ,\
            added_dt,added_by ,modify_dt,modify_by\
            )\
                VALUES\
                ({self.d_current_document_seed},9999,1,\
                N'{self.conformed_name}', N'{self.standard_industry_classification}', N'{self.irs_number}' ,N'{self.state_of_incorporation}',\
                N'{self.fiscal_year_end}', N'{self.form_type}', N'{self.street_1}',N'{self.city}', N'{self.state}',N'{self.zip}',N'{self.form_item1.item_text}',\
                N'{self.form_item1A.item_text}', N'{self.form_item1B.item_text}',N'{self.form_item2.item_text}',N'{self.form_item3.item_text}',N'{self.form_item4.item_text}',N'{self.form_item5.item_text}',\
                N'{self.form_item6.item_text}',N'{self.form_item7.item_text}',N'{self.form_item7A.item_text}', N'{self.form_item8.item_text}', N'{self.form_item9.item_text}',N'{self.form_item9A.item_text}',\
                N'{self.form_item9B.item_text}',N'{self.form_item9C.item_text}',N'{self.form_item10.item_text}',N'{self.form_item11.item_text}',N'{self.form_item12}.item_text',N'{self.form_item13.item_text}',\
                N'{self.form_item14.item_text}',N'{self.form_item15.item_text}',N'{self.form_item16.item_text}',\
                CURRENT_TIMESTAMP, N'Mohan Hanumantha',CURRENT_TIMESTAMP, N'Mohan Hanumantha')"





        # N'{self.fiscal_year_end}', N'{self.form_type}', N'{self.street_1}',N'{self.city}', N'{self.state}',N'{self.zip}',N'{self.form_item1}',\
        
        
       
        


        try:
            # Execute the SQL query
            cursor.execute(sql)

            # Commit the transaction
            conn.commit()

            print("Record inserted successfully!")
        except Exception as e:
            # Rollback the transaction if any error occurs
            conn.rollback()
            print(f"Error: {str(e)}")

        # Close the cursor and connection
        cursor.close()
        conn.close()


    def insertSeedData(self):

        # Establish a connection to the SQL Server database
        conn = pyodbc.connect('DRIVER={ODBC Driver 18 for SQL Server};SERVER=earthdevdb.database.windows.net;UID=earthdevdbadmin@earthdevdb.database.windows.net;PWD=3q45yE3fEgQej8h!@;database=earth-dev')
    
        # Create a cursor object to execute SQL queries
        cursor = conn.cursor()

        # Construct the INSERT INTO statement
        sql = f"INSERT INTO dbo.t_sec_document( \
            document_id , reporting_year, reporting_quarter, \
            conformed_name ,sic_code, irs_number, state_of_incorporation ,fiscal_year_end ,form_type,street_1,city ,state , zip,\
            form_item0 ,form_item1 ,form_item1A ,form_item1B ,form_item2 ,form_item3 ,form_item4 ,form_item5 ,form_item6 ,form_item7 ,form_item7A ,form_item8 ,\
            form_item9 ,form_item9A ,form_item9B ,form_item9C ,form_item10 ,form_item11 ,form_item12 ,form_item13 ,form_item14 ,form_item15 ,form_item16 ,\
            added_dt,added_by ,modify_dt,modify_by\
            )\
                VALUES\
                (1000,9999,1,\
                NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,\
                NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,\
                CURRENT_TIMESTAMP, N'Mohan Hanumantha',CURRENT_TIMESTAMP, N'Mohan Hanumantha')"

        try:
            # Execute the SQL query
            cursor.execute(sql)

            # Commit the transaction
            conn.commit()

            print("Record inserted successfully!")
        except Exception as e:
            # Rollback the transaction if any error occurs
            conn.rollback()
            print(f"Error: {str(e)}")

        # Close the cursor and connection
        cursor.close()
        conn.close()
