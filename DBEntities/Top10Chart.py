"""
Python implementation of sp_load_top10_exposure_data stored procedure.
This module provides functionality to load top 10 exposure data for charts.
"""

from datetime import datetime
from typing import Optional
import pandas as pd
import warnings

# Suppress pandas warning about DBAPI2 connections
warnings.filterwarnings(
    'ignore', message='pandas only supports SQLAlchemy connectable')


class Top10ExposureChartManager:
    """Processes and loads top 10 exposure data for chart generation."""

    def __init__(self, db_connection):
        """
        Initialize the processor with a database connection.

        Args:
            db_connection: Database connection object (e.g., SQLAlchemy engine or connection)
        """
        self.conn = db_connection

    def load_top10_exposure_data(self, company_name: str, sector_id: int, year: int) -> pd.DataFrame:
        """
        Load and process top 10 exposure data for a company and sector.

        Args:
            company_name: Name of the company
            sector_id: ID of the sector
            year: Year for the analysis

        Returns:
            DataFrame containing the processed top 10 exposure data
        """
        # Step 1: Get top 10 sector exposures
        top10_sector_query = """
            SELECT exposure_path_name 
            FROM t_sector_exp_insights 
            WHERE year = %s AND sector_id = %s 
            ORDER BY score_normalized DESC
            LIMIT 10
        """
        chart1_df = pd.read_sql(
            top10_sector_query,
            self.conn,
            params=(year, sector_id)
        )
        chart1_df.columns = ['top10_sector_exposure']
        chart1_df['degree_of_control_sector'] = None
        chart1_df['degree_of_control_company'] = None
        chart1_df['degree_of_control_sector_normalized'] = None
        chart1_df['degree_of_control_company_normalized'] = None
        chart1_df['top10_company_exposure'] = None
        chart1_df['unique_key'] = range(1, len(chart1_df) + 1)

        # Step 2: Get degree of control (Sector Level - Exposure vs. Mitigation)
        sector_exposure_query = """
            SELECT exposure_path_name, AVG(score) as degree_of_control_sector
            FROM t_sector_exp_mitigation_insights 
            WHERE sector_id = %s AND year = %s
            GROUP BY exposure_path_name
        """
        sector_exposure_df = pd.read_sql(
            sector_exposure_query,
            self.conn,
            params=(sector_id, year)
        )
        sector_exposure_df.columns = [
            'sector_exposure', 'degree_of_control_sector']

        # Update chart1 with sector exposure data
        chart1_df = chart1_df.merge(
            sector_exposure_df,
            left_on='top10_sector_exposure',
            right_on='sector_exposure',
            how='left',
            suffixes=('', '_sector')
        )
        chart1_df['degree_of_control_sector'] = chart1_df['degree_of_control_sector_sector']
        chart1_df = chart1_df.drop(
            columns=['sector_exposure', 'degree_of_control_sector_sector'], errors='ignore')

        # Step 3: Get degree of control (Company Level - Exposure vs. Mitigation)
        company_exposure_query = """
            SELECT exp.exposure_path_name, AVG(insights.score) as degree_of_control_company
            FROM t_mitigation_exp_insights insights
            INNER JOIN t_exposure_pathway exp ON exp.exposure_path_id = insights.exposure_path_id
            INNER JOIN t_document doc ON doc.document_id = insights.document_id 
                AND doc.company_name = %s
            WHERE insights.year = %s
            GROUP BY exp.exposure_path_name
        """
        company_exposure_df = pd.read_sql(
            company_exposure_query,
            self.conn,
            params=(company_name, year)
        )
        company_exposure_df.columns = [
            'company_exposure', 'degree_of_control_company']

        # Update chart1 with company exposure data
        chart1_df = chart1_df.merge(
            company_exposure_df,
            left_on='top10_sector_exposure',
            right_on='company_exposure',
            how='left',
            suffixes=('', '_company')
        )
        chart1_df['degree_of_control_company'] = chart1_df['degree_of_control_company_company']
        chart1_df = chart1_df.drop(
            columns=['company_exposure', 'degree_of_control_company_company'], errors='ignore')

        # Step 4: Get top 10 exposure pathways (Company Level)
        company_top10_query = """
            SELECT exp.exposure_path_name, AVG(insights.score) as sc
            FROM t_exposure_pathway_insights insights
            INNER JOIN t_exposure_pathway exp ON exp.exposure_path_id = insights.exposure_path_id
            INNER JOIN t_document doc ON doc.document_id = insights.document_id 
                AND doc.company_name = %s
            WHERE insights.year = %s
            GROUP BY exp.exposure_path_name
            ORDER BY sc DESC
            LIMIT 10
        """
        company_top10_df = pd.read_sql(
            company_top10_query,
            self.conn,
            params=(company_name, year)
        )
        company_top10_df.columns = ['top10_company_exposure', 'score']
        company_top10_df['unique_key'] = range(1, len(company_top10_df) + 1)

        # Update chart1 with company top10 exposure data
        chart1_df = chart1_df.merge(
            company_top10_df[['unique_key', 'top10_company_exposure']],
            on='unique_key',
            how='left',
            suffixes=('', '_top10')
        )
        chart1_df['top10_company_exposure'] = chart1_df['top10_company_exposure_top10']
        chart1_df = chart1_df.drop(
            columns=['top10_company_exposure_top10'], errors='ignore')

        # Step 5: Calculate normalized values
        max_sector_control = chart1_df['degree_of_control_sector'].max()
        if pd.notna(max_sector_control) and max_sector_control > 0:
            chart1_df['degree_of_control_sector_normalized'] = (
                chart1_df['degree_of_control_sector'] /
                max_sector_control * 100
            )
            chart1_df['degree_of_control_company_normalized'] = (
                chart1_df['degree_of_control_company'] /
                max_sector_control * 100
            )

        # Step 6: Delete existing records for this combination
        delete_query = """
            DELETE FROM t_chart_top10_exposures 
            WHERE sector_id = %s AND year = %s AND company_name = %s
        """
        cursor = self.conn.cursor()
        cursor.execute(delete_query, (sector_id, year, company_name))
        self.conn.commit()

        # Step 7: Insert new records
        current_timestamp = datetime.now()
        added_by = 'Mohan Hanumantha'

        for _, row in chart1_df.iterrows():
            insert_query = """
                INSERT INTO t_chart_top10_exposures (
                    sector_id, year, company_name, top10_sector_exposure,
                    degree_of_control_sector, degree_of_control_company,
                    degree_of_control_sector_normalized, degree_of_control_company_normalized,
                    top10_company_exposure, added_dt, added_by, modify_dt, modify_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (
                sector_id, year, company_name,
                row['top10_sector_exposure'],
                row['degree_of_control_sector'],
                row['degree_of_control_company'],
                row['degree_of_control_sector_normalized'],
                row['degree_of_control_company_normalized'],
                row['top10_company_exposure'],
                current_timestamp, added_by, current_timestamp, added_by
            ))
        self.conn.commit()
        cursor.close()

        # Step 8: Retrieve and return the final results
        result_query = """
            SELECT * FROM t_chart_top10_exposures 
            WHERE sector_id = %s AND year = %s AND company_name = %s
            ORDER BY degree_of_control_sector DESC
        """
        result_df = pd.read_sql(result_query, self.conn,
                                params=(sector_id, year, company_name))

        return result_df
