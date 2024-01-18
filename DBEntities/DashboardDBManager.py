from pathlib import Path
import sys
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

from DBEntities.DashboardDBEntitties import ExposurePathwayDBEntity, InternalizationDBEntity
from DBEntities.DataSourceDBEntity import DataSourceDBEntity
import pyodbc



DEV_DB_CONNECTION_STRING = 'DRIVER={ODBC Driver 18 for SQL Server};SERVER=earthdevdb.database.windows.net;UID=earthdevdbadmin@earthdevdb.database.windows.net;PWD=3q45yE3fEgQej8h!@;database=earth-dev'
TEST_DB_CONNECTION_STRING = 'DRIVER={ODBC Driver 18 for SQL Server};SERVER=earthdevdb.database.windows.net;UID=earthdevdbadmin@earthdevdb.database.windows.net;PWD=3q45yE3fEgQej8h!@;database=earth-test'


class DashboardDBManager():

    def __init__(self, database_context: None) -> None:

        connection_string = ''

        if (database_context == 'Development'):
            connection_string = DEV_DB_CONNECTION_STRING
        elif (database_context == 'Test'):
            connection_string = TEST_DB_CONNECTION_STRING
        else:
            raise Exception("Database context Undefined")

        self.dbConnection = pyodbc.connect(connection_string)

        self.dashboard_data_list = []

    def get_exposure_insights_by_company(self, company_name: str, year: int, content_type: int):

        try:
            cursor = self.dbConnection.cursor()

            sql = "SELECT doc.company_name Company,doc.year Year,lookups.data_lookups_description Document_Type,esg.esg_category_name ESG_Category,  exp.exposure_path_name Exposure_Pathway,\
                            count(*) Clusters, AVG(insights.score_normalized) Score\
                            FROM t_exposure_pathway_insights insights \
                                inner join t_exposure_pathway exp on exp.exposure_path_id = insights.exposure_path_id\
                                inner join t_impact_category imp on exp.impact_category_id = imp.impact_category_id\
                                inner join t_esg_category esg on imp.esg_category_id = esg.esg_category_id\
                                inner join t_document doc on doc.document_id = insights.document_id and doc.company_name =? and doc.year = ? and content_type = ?\
                                inner join t_data_lookups lookups on lookups.data_lookups_id = doc.content_type\
                            GROUP by doc.company_name  ,doc.year ,lookups.data_lookups_description,esg.esg_category_name ,  exp.exposure_path_name\
                            ORDER BY  doc.company_name,doc.year, lookups.data_lookups_description,esg.esg_category_name, exp.exposure_path_name\
                            "
            cursor.execute(sql, company_name, year, content_type)

            rows = cursor.fetchall()
            for row in rows:
                dashboard_entity = ExposurePathwayDBEntity(
                    Sector='Test',
                    Company=row.Company,
                    Year=row.Year,
                    Document_Type=row.Document_Type,
                    ESG_Category=row.ESG_Category,
                    Exposure_Pathway=row.Exposure_Pathway,
                    Clusters=row.Clusters,
                    Score=row.Score
                )
                self.dashboard_data_list.append(dashboard_entity)
            cursor.close()
        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

        # print(self.dashboard_data_list)
        return self.dashboard_data_list

    def get_exposure_insights(self):

        # count = len(self.dashboard_data_list)
        # if count > 0:
        #     print('Loading data from Cache')
        #     return self.dashboard_data_list
        try:
            cursor = self.dbConnection.cursor()
            cursor.execute("\
                            SELECT sector_lookup.data_lookups_description Sector,  doc.company_name Company,doc.year Year,lookups.data_lookups_description Document_Type,esg.esg_category_name ESG_Category,  exp.exposure_path_name Exposure_Pathway,\
                            count(*) Clusters, AVG(insights.score_normalized) Score\
                            FROM t_exposure_pathway_insights insights \
                                inner join t_exposure_pathway exp on exp.exposure_path_id = insights.exposure_path_id\
                                inner join t_impact_category imp on exp.impact_category_id = imp.impact_category_id\
                                inner join t_esg_category esg on imp.esg_category_id = esg.esg_category_id\
                                inner join t_document doc on doc.document_id = insights.document_id\
                                inner join t_data_lookups lookups on lookups.data_lookups_id = doc.content_type\
                                inner join t_data_lookups sector_lookup on sector_lookup.data_lookups_id = insights.sector_id and sector_lookup.data_lookups_group_id = 5\
                            GROUP by  sector_lookup.data_lookups_description,doc.company_name  ,doc.year ,lookups.data_lookups_description,esg.esg_category_name ,  exp.exposure_path_name\
                            ORDER BY   sector_lookup.data_lookups_description,doc.company_name,doc.year, lookups.data_lookups_description,esg.esg_category_name, exp.exposure_path_name\
                           ")
            rows = cursor.fetchall()
            for row in rows:
                dashboard_entity = ExposurePathwayDBEntity(
                    Sector=row.Sector,
                    Company=row.Company,
                    Year=row.Year,
                    Document_Type=row.Document_Type,
                    ESG_Category=row.ESG_Category,
                    Exposure_Pathway=row.Exposure_Pathway,
                    Clusters=row.Clusters,
                    Score=row.Score
                )
                self.dashboard_data_list.append(dashboard_entity)
            cursor.close()
        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

        return self.dashboard_data_list

    def get_internalization_insights(self):

        # count = len(self.dashboard_data_list)
        # if count > 0:
        #     print('Loading data from Cache')
        #     return self.dashboard_data_list

        # print('Loading data from Database')

        try:
            cursor = self.dbConnection.cursor()
            cursor.execute("\
                           SELECT doc.company_name 'Company',doc.year 'Year',lookups.data_lookups_description 'Document_Type',esg.esg_category_name 'ESG_Category', exp.exposure_path_name 'Exposure_Pathway', \
                                int.internalization_name 'Internalization', count(*) Clusters, AVG(insights.score_normalized) Score\
                            FROM t_internalization_insights insights\
                                INNER JOIN t_internalization int on int.internalization_id = insights.internalization_id \
                                INNER JOIN t_exposure_pathway exp on exp.exposure_path_id = int.exposure_path_id\
                                inner join t_impact_category imp on exp.impact_category_id = imp.impact_category_id\
                                inner join t_esg_category esg on imp.esg_category_id = esg.esg_category_id\
                                inner join t_document doc on doc.document_id = insights.document_id\
                                inner join t_data_lookups lookups on lookups.data_lookups_id = doc.content_type\
                            GROUP by\
                                doc.company_name  ,doc.year ,lookups.data_lookups_description,esg.esg_category_name ,exp.exposure_path_name , int.internalization_name\
                            ORDER BY  doc.company_name,doc.year, lookups.data_lookups_description,esg.esg_category_name, exp.exposure_path_name ,int.internalization_name")
            rows = cursor.fetchall()
            for row in rows:
                dashboard_entity = InternalizationDBEntity(
                    Company=row.Company,
                    Year=row.Year,
                    Document_Type=row.Document_Type,
                    ESG_Category=row.ESG_Category,
                    Exposure_Pathway=row.Exposure_Pathway,
                    Internalization=row.Internalization,
                    Clusters=row.Clusters,
                    Score=row.Score
                )
                self.dashboard_data_list.append(dashboard_entity)
            cursor.close()
        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

        return self.dashboard_data_list

    def get_sector_exposure_insight(self, company_name: str, year: int):

        sector_id: int

        try:
            cursor = self.dbConnection.cursor()
            sector_sql = "select sector_id from t_sec_company_sector_map where company_name = ?"
            cursor.execute(sector_sql, company_name)

            sector_id = cursor.fetchone()[0]

            sql = "SELECT esg_category_name ESG_Category, exposure_path_name Exposure_Pathway, cluster_count Clusters, score_normalized  Score from t_sector_exp_insights where sector_id = ? and year = ?"
            cursor.execute(sql, sector_id, year)

            rows = cursor.fetchall()
            for row in rows:
                dashboard_entity = ExposurePathwayDBEntity(
                    Sector='Test',
                    Company='',
                    Year=0,
                    Document_Type='Sector',
                    ESG_Category=row.ESG_Category,
                    Exposure_Pathway=row.Exposure_Pathway,
                    Clusters=row.Clusters,
                    Score=row.Score
                )
                self.dashboard_data_list.append(dashboard_entity)
            cursor.close()
        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc


        return self.dashboard_data_list

    def get_sector_exposure_company_insight(self, company_name: str, year: int, content_type):

        self.dashboard_data_list = self.get_exposure_insights_by_company(company_name,year,content_type)

        sector_id: int

        try:
            cursor = self.dbConnection.cursor()
            sector_sql = "select sector_id from t_sec_company_sector_map where company_name = ?"
            cursor.execute(sector_sql, company_name)

            sector_id = cursor.fetchone()[0]

            sql = "SELECT esg_category_name ESG_Category, exposure_path_name Exposure_Pathway, cluster_count Clusters, score_normalized  Score from t_sector_exp_insights where sector_id = ? and year = ?"
            cursor.execute(sql, sector_id, year)

            rows = cursor.fetchall()
            for row in rows:
                dashboard_entity = ExposurePathwayDBEntity(
                    Company='',
                    Year=0,
                    Document_Type='Sector',
                    ESG_Category=row.ESG_Category,
                    Exposure_Pathway=row.Exposure_Pathway,
                    Clusters=row.Clusters,
                    Score=row.Score
                )
                self.dashboard_data_list.append(dashboard_entity)
            cursor.close()
        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

        return self.dashboard_data_list


# dashboard_data_list = DashboardDBManager(
#     "Test").get_exposure_insights()
# dashboard_data_list = DashboardDBManager(
#     "Test").get_sector_exposure_insight('Anglo American', 2010,1)


# print('Success')
