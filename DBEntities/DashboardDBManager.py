from pathlib import Path
import sys
sys.path.append(str(Path(sys.argv[0]).resolve().parent.parent))

from DBEntities.DashboardDBEntitties import ExposurePathwayDBEntity, InternalizationDBEntity, MitigationDBEntity
from DBEntities.DataSourceDBEntity import DataSourceDBEntity
import pyodbc
import pandas as pd


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
                    Sector='',
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

    def get_internalization_insights(self,company_name: str, year: int, content_type: int):

        try:
            cursor = self.dbConnection.cursor()
            if(year == 0):
                sql = "SELECT  \
                            doc.company_name Company,doc.year Year,lookups.data_lookups_description Document_Type,esg.esg_category_name ESG_Category,  exp.exposure_path_name Exposure_Pathway,\
                            exp.exposure_path_name Exposure_Pathway, int.internalization_name Internalization,\
                            count(*) Clusters, AVG(insights.score_normalized) Score\
                            FROM t_exp_int_insights insights\
                                INNER JOIN t_exposure_pathway exp on exp.exposure_path_id = insights.exposure_path_id\
                                INNER JOIN t_internalization int on int.internalization_id = insights.internalization_id  and int.exposure_path_id = insights.exposure_path_id\
                                inner join t_impact_category imp on exp.impact_category_id = imp.impact_category_id\
                                inner join t_esg_category esg on imp.esg_category_id = esg.esg_category_id\
                                inner join t_document doc on doc.document_id = insights.document_id and doc.company_name = ? and content_type = ?\
                                inner join t_data_lookups lookups on lookups.data_lookups_id = doc.content_type\
                            GROUP by doc.company_name  ,doc.year ,lookups.data_lookups_description,esg.esg_category_name ,  exp.exposure_path_name,int.internalization_name\
                                    ORDER BY  doc.company_name,doc.year, lookups.data_lookups_description,esg.esg_category_name, exp.exposure_path_name,int.internalization_name"
                cursor.execute(sql, company_name, content_type)

            else:
                sql = "SELECT  \
                            doc.company_name Company,doc.year Year,lookups.data_lookups_description Document_Type,esg.esg_category_name ESG_Category,  exp.exposure_path_name Exposure_Pathway,\
                            exp.exposure_path_name Exposure_Pathway, int.internalization_name Internalization,\
                            count(*) Clusters, AVG(insights.score_normalized) Score\
                            FROM t_exp_int_insights insights\
                                INNER JOIN t_exposure_pathway exp on exp.exposure_path_id = insights.exposure_path_id\
                                INNER JOIN t_internalization int on int.internalization_id = insights.internalization_id  and int.exposure_path_id = insights.exposure_path_id\
                                inner join t_impact_category imp on exp.impact_category_id = imp.impact_category_id\
                                inner join t_esg_category esg on imp.esg_category_id = esg.esg_category_id\
                                inner join t_document doc on doc.document_id = insights.document_id and doc.company_name = ? and doc.year = ? and content_type = ?\
                                inner join t_data_lookups lookups on lookups.data_lookups_id = doc.content_type\
                            GROUP by doc.company_name  ,doc.year ,lookups.data_lookups_description,esg.esg_category_name ,  exp.exposure_path_name,int.internalization_name\
                                    ORDER BY  doc.company_name,doc.year, lookups.data_lookups_description,esg.esg_category_name, exp.exposure_path_name,int.internalization_name\
                "                            
                cursor.execute(sql, company_name, year, content_type)
                
            rows = cursor.fetchall()
            for row in rows:
                dashboard_entity = InternalizationDBEntity(
                    Sector='',
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

    def get_mitigation_insights(self, company_name: str, year: int, content_type: int):

        try:
            cursor = self.dbConnection.cursor()
            if (year == 0):
                sql = "SELECT doc.company_name Company,doc.year Year,lookups.data_lookups_description Document_Type,esg.esg_category_name ESG_Category,  exp.exposure_path_name Exposure_Pathway,\
                                int.internalization_name Internalization, mit.class_name,mit.sub_class_name, count(*) Clusters, AVG(insights.score_normalized) Score\
                       FROM t_mitigation_exp_int_insights insights\
                                INNER JOIN t_exposure_pathway exp on exp.exposure_path_id = insights.exposure_path_id\
                                INNER JOIN t_internalization int on int.internalization_id = insights.internalization_id  and int.exposure_path_id = insights.exposure_path_id\
                                inner join t_impact_category imp on exp.impact_category_id = imp.impact_category_id\
                                inner join t_esg_category esg on imp.esg_category_id = esg.esg_category_id\
                                INNER JOIN t_key_word_hits hits on insights.mitigation_keyword_hit_id = hits.key_word_hit_id\
                                INNER JOIN t_mitigation mit on hits.dictionary_id = mit.dictionary_id\
                                INNER JOIN t_document doc on doc.document_id = insights.document_id and doc.company_name =? and content_type = ?\
                                INNER JOIN t_data_lookups lookups on lookups.data_lookups_id = doc.content_type\
                        GROUP by doc.company_name  ,doc.year ,lookups.data_lookups_description,esg.esg_category_name ,  exp.exposure_path_name,int.internalization_name, mit.class_name,mit.sub_class_name\
                        ORDER BY   Score desc\
                    "
                cursor.execute(sql, company_name, content_type)

            else:
                sql = "SELECT doc.company_name Company,doc.year Year,lookups.data_lookups_description Document_Type,esg.esg_category_name ESG_Category,  exp.exposure_path_name Exposure_Pathway,\
                                int.internalization_name Internalization, mit.class_name Mitigation_Class,mit.sub_class_name Mitigation_Sub_Class, count(*) Clusters, AVG(insights.score_normalized) Score\
                       FROM t_mitigation_exp_int_insights insights\
                                INNER JOIN t_exposure_pathway exp on exp.exposure_path_id = insights.exposure_path_id\
                                INNER JOIN t_internalization int on int.internalization_id = insights.internalization_id  and int.exposure_path_id = insights.exposure_path_id\
                                inner join t_impact_category imp on exp.impact_category_id = imp.impact_category_id\
                                inner join t_esg_category esg on imp.esg_category_id = esg.esg_category_id\
                                INNER JOIN t_key_word_hits hits on insights.mitigation_keyword_hit_id = hits.key_word_hit_id\
                                INNER JOIN t_mitigation mit on hits.dictionary_id = mit.dictionary_id\
                                INNER JOIN t_document doc on doc.document_id = insights.document_id and doc.company_name = ? and doc.year = ? and content_type = ?\
                                INNER JOIN t_data_lookups lookups on lookups.data_lookups_id = doc.content_type\
                        GROUP by doc.company_name  ,doc.year ,lookups.data_lookups_description,esg.esg_category_name ,  exp.exposure_path_name,int.internalization_name, mit.class_name,mit.sub_class_name\
                        ORDER BY   Score desc\
                    "
                cursor.execute(sql, company_name, year, content_type)

            rows = cursor.fetchall()
            for row in rows:
                dashboard_entity = MitigationDBEntity(
                    Sector='',
                    Company=row.Company,
                    Year=row.Year,
                    Document_Type=row.Document_Type,
                    ESG_Category=row.ESG_Category,
                    Exposure_Pathway=row.Exposure_Pathway,
                    Internalization=row.Internalization,
                    Mitigation_Class=row.Mitigation_Class,
                    Mitigation_Sub_Class=row.Mitigation_Sub_Class,
                    Clusters=row.Clusters,
                    Score=row.Score
                )
                self.dashboard_data_list.append(dashboard_entity)
            cursor.close()
        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

        return self.dashboard_data_list

    def get_sector_exposure_insight(self, sector: str, year: int):

        sql = "SELECT insights.esg_category_name ESG_Category, insights.exposure_path_name Exposure_Pathway, insights.cluster_count Clusters, insights.score_normalized  Score\
                    from t_sector_exp_insights insights inner join  t_data_lookups lookups on insights.sector_id = lookups.data_lookups_id and  lookups.data_lookups_description =?\
                    where insights.[year] =?\
                  "
        cursor = self.dbConnection.cursor()
        try:

            cursor.execute(sql, sector, year)

            rows = cursor.fetchall()
            for row in rows:
                dashboard_entity = ExposurePathwayDBEntity(
                    Sector='',
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

    def get_sector_internalization_insight(self, sector: str, year: int):

        sql = "SELECT insights.esg_category_name ESG_Category, insights.exposure_path_name Exposure_Pathway, insights.internalization_name Internalization, insights.cluster_count Clusters, insights.score_normalized  Score\
                    from t_sector_exp_int_insights insights inner join  t_data_lookups lookups on insights.sector_id = lookups.data_lookups_id and  lookups.data_lookups_description =?\
                    where insights.[year] =?\
                  "
        cursor = self.dbConnection.cursor()
        try:

            cursor.execute(sql, sector, year)

            rows = cursor.fetchall()
            for row in rows:
                dashboard_entity = InternalizationDBEntity(
                    Sector='',
                    Company='',
                    Year=0,
                    Document_Type='Sector',
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

    def get_sector_mitigation_insight(self, sector: str, year: int):

        sql = "SELECT insights.esg_category_name ESG_Category, insights.exposure_path_name Exposure_Pathway, insights.internalization_name Internalization,insights.mitigation_class Mitigation_Class, insights.mitigation_sub_class Mitigation_Sub_Class, insights.cluster_count Clusters, insights.score_normalized  Score\
                    from t_sector_exp_int_mitigation_insights insights inner join  t_data_lookups lookups on insights.sector_id = lookups.data_lookups_id and  lookups.data_lookups_description =?\
                    where insights.[year] =?\
              "
        cursor = self.dbConnection.cursor()
        try:

            cursor.execute(sql, sector, year)

            rows = cursor.fetchall()
            for row in rows:
                dashboard_entity = MitigationDBEntity(
                    Sector='',
                    Company='',
                    Year=0,
                    Document_Type='Sector',
                    ESG_Category=row.ESG_Category,
                    Exposure_Pathway=row.Exposure_Pathway,
                    Internalization=row.Internalization,
                    Mitigation_Class = row.Mitigation_Class,
                    Mitigation_Sub_Class = row.Mitigation_Sub_Class,
                    Clusters=row.Clusters,
                    Score=row.Score
                )
                self.dashboard_data_list.append(dashboard_entity)
            cursor.close()
        except Exception as exc:
            print(f"Error: {str(exc)}")
            raise exc

        return self.dashboard_data_list




    # SECTOR

    def get_sector_list(self):

        sector_list = []

        sql = 'select l.data_lookups_description  sector from t_data_lookups l where data_lookups_group_id = 5 order by l.data_lookups_description'

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

    def get_company_list(self):
        company_list = []

        sql = 'select map.company_name company_name, lookups.data_lookups_description  sector from t_sec_company_sector_map map inner join t_data_lookups lookups on map.sector_id = lookups.data_lookups_id order by lookups.data_lookups_description, map.company_name'

        try:
            # Execute the SQL query
            cursor = self.dbConnection.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row in rows:
                db_entity = InternalizationDBEntity(    
                    Company=row.company_name,
                    Sector=row.sector           
                    )
                company_list.append(db_entity)

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

    def get_sector_company_year_doctype_list(self):

        l_sector = self.get_sector_list()
        l_sector_company = self.get_company_list()
        l_year = self.get_year_list()
        l_doc_type = self.get_doc_type_list()

        return l_sector, l_sector_company, l_year, l_doc_type


