#!/usr/bin/env python3
"""
Database Connection Test Script
Tests the GCC PostgreSQL database connection by reading from t_lookups table
"""

from Utilities.Lookups import DB_Connection
import sys
from pathlib import Path

# Add the parent directory to the path to import our modules
sys.path.append(str(Path(__file__).resolve().parent))


def main():
    """Test the database connection"""
    print("🔍 Testing GCC PostgreSQL Database Connection...")
    print("=" * 50)

    try:
        # Create DB_Connection instance
        db_conn = DB_Connection()

        print(
            f"🔗 Using connection string: {db_conn.DEV_DB_CONNECTION_STRING[:50]}...")
        print()

        # Test the connection
        result = db_conn.test_connection()

        print()
        print("=" * 50)

        if result["status"] == "success":
            print("🎉 Database connection test PASSED!")
            print(f"📈 Total records retrieved: {result['records_count']}")
        else:
            print("💥 Database connection test FAILED!")
            print(f"❌ Error: {result['message']}")
            print(f"🔍 Error type: {result['error_type']}")

    except Exception as e:
        print(f"💥 Unexpected error: {str(e)}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
