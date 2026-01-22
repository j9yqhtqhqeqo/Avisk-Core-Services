class Lookups:
    def __init__(self) -> None:
        self.Exposure_Pathway_Dictionary_Type = 1000
        self.Internalization_Dictionary_Type = 1001
        self.Mitigation_Dictionary_Type = 1002
        self.Mitigation_Exp_Insight_Type = 1003
        self.Mitigation_Int_Insight_Type = 1004
        self.Exp_Int_Insight_Type = 1005
        self.Mitigation_Exp_INT_Insight_Type = 1006
        self.Keyword_Hit_Save = 2000
        self.Exposure_Save = 2001
        self.Internalization_Save = 2002


class Content_Type:
    def __init__(self) -> None:
        self.sustainbility_report = 1
        self.TenK_Report = 2


class Processing_Type:
    def __init__(self) -> None:
        self.KEYWORD_GEN_EXP = 1
        self.KEYWORD_GEN_INT = 2
        self.KEYWORD_GEN_MIT = 3
        self.EXPOSURE_INSIGHTS_GEN = 4
        self.INTERNALIZATION_INSIGHTS_GEN = 5
        self.Mitigation_Exp_Insight_GEN = 6
        self.Mitigation_Int_Insight_GEN = 7
        self.Exp_Int_Insight_GEN = 8
        self.Mitigation_Exp_INT_Insight_GEN = 9


class DB_Connection:
    def __init__(self):
        import os

        # Get password from Secret Manager or environment variable
        password = self._get_db_password()

        # Determine environment and connection method
        if os.getenv('ENVIRONMENT') == 'cloud':
            # Cloud environment using Unix socket
            self.DEV_DB_CONNECTION_STRING = f'host=/cloudsql/avisk-ai-platform:us-central1:avisk-core-dev dbname=avisk-core-dev-db1 user=avisk-admin password={password}'
        else:
            # Local development via Cloud SQL Auth Proxy
            self.DEV_DB_CONNECTION_STRING = f'host=localhost port=5434 dbname=avisk-core-dev-db1 user=avisk-admin password={password}'

    def _get_db_password(self):
        """Retrieve database password from Google Secret Manager"""
        try:
            from google.cloud import secretmanager
            client = secretmanager.SecretManagerServiceClient()
            project_id = "avisk-ai-platform"
            secret_name = "db-password"
            name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            password = response.payload.data.decode("UTF-8")
            print("✅ Retrieved database password from Google Secret Manager")
            return password
        except Exception as e:
            raise Exception("Unable to retrieve password from Secret Manager")

    def test_connection(self):
        """Test database connection by reading data from t_lookups table"""
        import psycopg2
        import psycopg2.extras

        connection = None
        cursor = None

        try:
            # Establish connection
            connection = psycopg2.connect(self.DEV_DB_CONNECTION_STRING)
            cursor = connection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)

            # Test query - get first 5 records from t_lookups
            test_query = "SELECT * FROM t_data_lookups LIMIT 5;"
            cursor.execute(test_query)

            # Fetch results
            results = cursor.fetchall()

            print(f"✅ Database connection successful!")
            print(f"📊 Retrieved {len(results)} records from t_lookups table:")

            for i, record in enumerate(results, 1):
                print(f"   {i}. {dict(record)}")

            return {
                "status": "success",
                "message": "Database connection test passed",
                "records_count": len(results),
                "sample_data": [dict(record) for record in results]
            }

        except psycopg2.Error as db_error:
            error_msg = f"Database error: {str(db_error)}"
            print(f"❌ {error_msg}")
            return {
                "status": "error",
                "message": error_msg,
                "error_type": "database_error"
            }
        except Exception as general_error:
            error_msg = f"Connection error: {str(general_error)}"
            print(f"❌ {error_msg}")
            return {
                "status": "error",
                "message": error_msg,
                "error_type": "general_error"
            }
        finally:
            # Clean up resources
            if cursor:
                cursor.close()
            if connection:
                connection.close()
                print("🔌 Database connection closed.")
