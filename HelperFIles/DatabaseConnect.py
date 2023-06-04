# import pyodbc
# cnxn = pyodbc.connect('DRIVER={ODBC Driver 18 for SQL Server};SERVER=earthdevdb.database.windows.net;UID=earthdevdbadmin@earthdevdb.database.windows.net;PWD=3q45yE3fEgQej8h!@;database=earth-dev')
# cursor = cnxn.cursor()
# cursor.execute("SELECT CustomerId ,Name ,Location,Email from customers;") 
# row = cursor.fetchone() 
# while row: 
#     print(row[0], "   ", row[1],"   ", row[2],"  " , row[3])
#     row = cursor.fetchone()
# cursor.close()
# cnxn.close()


# import pyodbc
# cnxn = pyodbc.connect('DRIVER={ODBC Driver 18 for SQL Server};SERVER=earthdevdb.database.windows.net;UID=mytestuser1@earthdevdb.database.windows.net;PWD=J653w57w341!@;database=earth-dev')
# cursor = cnxn.cursor()
# cursor.execute("SELECT CustomerId ,Name ,Location,Email from customers;") 
# row = cursor.fetchone() 
# while row: 
#     print(row[0], "   ", row[1],"   ", row[2],"  " , row[3])
#     row = cursor.fetchone()
# cursor.close()
# cnxn.close()
