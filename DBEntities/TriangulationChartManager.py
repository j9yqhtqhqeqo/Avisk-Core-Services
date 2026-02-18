import psycopg2
import psycopg2.extras
from Utilities.Lookups import DB_Connection
from Utilities.LoggingServices import logGenerator

DB_CONNECTION_STRING = DB_Connection().DB_CONNECTION_STRING


class TriangulationChartManager:
    """
    Manages triangulation chart data generation for sector and company analysis.
    Converted from SQL Server stored procedure sp_load_triangulation_chart_data
    """

    def __init__(self, db_connection) -> None:
        self.dbConnection = db_connection

    def load_triangulation_chart_data(self, company_name: str, sector_id: int, year: int):
        """
        Load triangulation chart data for a specific company, sector, and year.

        Calculates normalized scores for:
        - Sector: Exposure-Internalization, Exposure-Mitigation, Internalization-Mitigation
        - Company: Same three combinations

        Args:
            company_name: Company name to analyze
            sector_id: Sector ID
            year: Year to analyze
        """
        try:
            cursor = self.dbConnection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)

            # Step 1: Get Internalization-Mitigation sector scores
            sql_int_mit = """
                SELECT sector_id, year, exposure_path_name, AVG(score) as score 
                FROM t_sector_exp_int_mitigation_insights
                WHERE year = %s AND sector_id = %s
                GROUP BY sector_id, year, exposure_path_name
                ORDER BY year, score DESC, exposure_path_name
            """
            cursor.execute(sql_int_mit, (year, sector_id))
            int_mit_data = cursor.fetchall()

            # Step 2: Get Exposure-Mitigation sector scores
            sql_exp_mit = """
                SELECT sector_id, year, exposure_path_name, AVG(score) as score 
                FROM t_sector_exp_mitigation_insights
                WHERE year = %s AND sector_id = %s
                GROUP BY sector_id, year, exposure_path_name        
                ORDER BY year, score DESC, exposure_path_name
            """
            cursor.execute(sql_exp_mit, (year, sector_id))
            exp_mit_data = cursor.fetchall()

            # Step 3: Get Exposure-Internalization sector scores
            sql_exp_int = """
                SELECT sector_id, year, exposure_path_name, AVG(score) as score 
                FROM t_sector_exp_int_insights
                WHERE year = %s AND sector_id = %s
                GROUP BY sector_id, year, exposure_path_name
                ORDER BY year, score DESC, exposure_path_name
            """
            cursor.execute(sql_exp_int, (year, sector_id))
            exp_int_data = cursor.fetchall()

            # Step 4: Build triangulation scores dictionary
            triangulation_scores = {}
            for row in int_mit_data:
                key = row['exposure_path_name']
                triangulation_scores[key] = {
                    'sector_id': row['sector_id'],
                    'year': row['year'],
                    'sector_exposure_path_name': row['exposure_path_name'],
                    'sector_internalization_mitigation_score': row['score'],
                    'sector_exposure_mitigation_score': None,
                    'sector_exposure_internalization_score': None,
                    'company_name': company_name,
                    'company_exposure_internalization_score': None,
                    'company_exposure_mitigation_score': None,
                    'company_internalization_mitigation_score': None
                }

            # Step 5: Merge Exposure-Mitigation scores
            for row in exp_mit_data:
                key = row['exposure_path_name']
                if key in triangulation_scores:
                    triangulation_scores[key]['sector_exposure_mitigation_score'] = row['score']

            # Step 6: Merge Exposure-Internalization scores
            for row in exp_int_data:
                key = row['exposure_path_name']
                if key in triangulation_scores:
                    triangulation_scores[key]['sector_exposure_internalization_score'] = row['score']

            # Step 7: Normalize sector scores
            if triangulation_scores:
                max_exp_int = max((v['sector_exposure_internalization_score'] or 0
                                  for v in triangulation_scores.values()), default=0)
                max_exp_mit = max((v['sector_exposure_mitigation_score'] or 0
                                  for v in triangulation_scores.values()), default=0)
                max_int_mit = max((v['sector_internalization_mitigation_score'] or 0
                                  for v in triangulation_scores.values()), default=0)

                for data in triangulation_scores.values():
                    if max_exp_int > 0 and data['sector_exposure_internalization_score']:
                        data['sector_exposure_internalization_score_normalized'] = \
                            (data['sector_exposure_internalization_score'] /
                             max_exp_int) * 100
                    else:
                        data['sector_exposure_internalization_score_normalized'] = None

                    if max_exp_mit > 0 and data['sector_exposure_mitigation_score']:
                        data['sector_exposure_mitigation_score_normalized'] = \
                            (data['sector_exposure_mitigation_score'] /
                             max_exp_mit) * 100
                    else:
                        data['sector_exposure_mitigation_score_normalized'] = None

                    if max_int_mit > 0 and data['sector_internalization_mitigation_score']:
                        data['sector_internalization_mitigation_score_normalized'] = \
                            (data['sector_internalization_mitigation_score'] /
                             max_int_mit) * 100
                    else:
                        data['sector_internalization_mitigation_score_normalized'] = None

            # Step 8: Get company Exposure-Mitigation scores
            sql_company_exp_mit = """
                SELECT exp.exposure_path_name, AVG(insights.score) as score
                FROM t_mitigation_exp_insights insights
                INNER JOIN t_exposure_pathway exp ON exp.exposure_path_id = insights.exposure_path_id
                INNER JOIN t_document doc ON doc.document_id = insights.document_id AND doc.company_name = %s
                WHERE insights.year = %s AND insights.sector_id = %s
                GROUP BY exp.exposure_path_name
            """
            cursor.execute(sql_company_exp_mit,
                           (company_name, year, sector_id))
            company_exp_mit = cursor.fetchall()

            for row in company_exp_mit:
                key = row['exposure_path_name']
                if key in triangulation_scores:
                    triangulation_scores[key]['company_exposure_mitigation_score'] = row['score']

            # Step 9: Get company Exposure-Internalization scores
            sql_company_exp_int = """
                SELECT exp.exposure_path_name, AVG(insights.score) as score
                FROM t_exp_int_insights insights
                INNER JOIN t_exposure_pathway exp ON exp.exposure_path_id = insights.exposure_path_id
                INNER JOIN t_document doc ON doc.document_id = insights.document_id AND doc.company_name = %s
                WHERE insights.year = %s
                GROUP BY exp.exposure_path_name
            """
            cursor.execute(sql_company_exp_int, (company_name, year))
            company_exp_int = cursor.fetchall()

            for row in company_exp_int:
                key = row['exposure_path_name']
                if key in triangulation_scores:
                    triangulation_scores[key]['company_exposure_internalization_score'] = row['score']

            # Step 10: Get company Internalization-Mitigation scores
            sql_company_int_mit = """
                SELECT exp.exposure_path_name, AVG(insights.score) as score
                FROM t_mitigation_exp_int_insights insights
                INNER JOIN t_exposure_pathway exp ON exp.exposure_path_id = insights.exposure_path_id
                INNER JOIN t_document doc ON doc.document_id = insights.document_id AND doc.company_name = %s
                WHERE insights.year = %s
                GROUP BY exp.exposure_path_name
            """
            cursor.execute(sql_company_int_mit, (company_name, year))
            company_int_mit = cursor.fetchall()

            for row in company_int_mit:
                key = row['exposure_path_name']
                if key in triangulation_scores:
                    triangulation_scores[key]['company_internalization_mitigation_score'] = row['score']

            # Step 11: Normalize company scores (against sector max)
            for data in triangulation_scores.values():
                if max_exp_mit > 0 and data['company_exposure_mitigation_score']:
                    data['company_exposure_mitigation_score_normalized'] = \
                        (data['company_exposure_mitigation_score'] /
                         max_exp_mit) * 100
                else:
                    data['company_exposure_mitigation_score_normalized'] = None

                if max_exp_int > 0 and data['company_exposure_internalization_score']:
                    data['company_exposure_internalization_score_normalized'] = \
                        (data['company_exposure_internalization_score'] /
                         max_exp_int) * 100
                else:
                    data['company_exposure_internalization_score_normalized'] = None

                if max_int_mit > 0 and data['company_internalization_mitigation_score']:
                    data['company_internalization_mitigation_score_normalized'] = \
                        (data['company_internalization_mitigation_score'] /
                         max_int_mit) * 100
                else:
                    data['company_internalization_mitigation_score_normalized'] = None

            # Step 12: Delete existing data for this company/sector/year
            sql_delete = """
                DELETE FROM t_chart_triangulation 
                WHERE sector_id = %s AND year = %s AND company_name = %s
            """
            cursor.execute(sql_delete, (sector_id, year, company_name))

            # Step 13: Insert new triangulation data
            sql_insert = """
                INSERT INTO t_chart_triangulation(
                    sector_id, year, sector_exposure_path_name,
                    sector_exposure_internalization_score, sector_exposure_mitigation_score,
                    sector_internalization_mitigation_score, sector_exposure_internalization_score_normalized,
                    sector_exposure_mitigation_score_normalized, sector_internalization_mitigation_score_normalized,
                    company_name, company_exposure_internalization_score, company_exposure_mitigation_score,
                    company_internalization_mitigation_score, company_exposure_internalization_score_normalized,
                    company_exposure_mitigation_score_normalized, company_internalization_mitigation_score_normalized,
                    added_dt, added_by, modify_dt, modify_by
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    CURRENT_TIMESTAMP, %s, CURRENT_TIMESTAMP, %s
                )
            """

            for data in triangulation_scores.values():
                cursor.execute(sql_insert, (
                    data['sector_id'],
                    data['year'],
                    data['sector_exposure_path_name'],
                    data['sector_exposure_internalization_score'],
                    data['sector_exposure_mitigation_score'],
                    data['sector_internalization_mitigation_score'],
                    data['sector_exposure_internalization_score_normalized'],
                    data['sector_exposure_mitigation_score_normalized'],
                    data['sector_internalization_mitigation_score_normalized'],
                    data['company_name'],
                    data['company_exposure_internalization_score'],
                    data['company_exposure_mitigation_score'],
                    data['company_internalization_mitigation_score'],
                    data['company_exposure_internalization_score_normalized'],
                    data['company_exposure_mitigation_score_normalized'],
                    data['company_internalization_mitigation_score_normalized'],
                    'MOHAN HANUMANTHA',
                    'MOHAN HANUMANTHA'
                ))

            self.dbConnection.commit()

            # Step 14: Return the results
            sql_select = """
                SELECT * FROM t_chart_triangulation 
                WHERE sector_id = %s AND year = %s AND company_name = %s
                ORDER BY year, sector_exposure_path_name
            """
            cursor.execute(sql_select, (sector_id, year, company_name))
            results = cursor.fetchall()

            cursor.close()

            print(
                f"Loaded {len(results)} triangulation chart records for {company_name}, Sector {sector_id}, Year {year}")
            return results

        except Exception as exc:
            self.dbConnection.rollback()
            print(f"Error loading triangulation chart data: {str(exc)}")
            raise exc
