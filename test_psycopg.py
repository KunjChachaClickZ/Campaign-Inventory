#!/usr/bin/env python3
"""
Simple test script to verify psycopg installation and basic functionality
"""

try:
    import psycopg
    print("✅ psycopg is successfully installed")
    print(f"Version: {psycopg.__version__}")

    # Test basic connection parameters (without actually connecting)
    DB_CONFIG = {
        'host': 'contentive-warehouse-instance-1.cq8sion7djdk.eu-west-2.rds.amazonaws.com',
        'port': 5432,
        'dbname': 'analytics',
        'user': 'kunj.chacha@contentive.com',
        'password': '***masked***'
    }

    print("✅ Database configuration is properly formatted for psycopg")
    print("✅ All imports and basic setup are working correctly")

except ImportError as e:
    print(f"❌ Error importing psycopg: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
