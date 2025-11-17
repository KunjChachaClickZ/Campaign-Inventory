import os
import json
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS

# Try to import psycopg2, fallback to psycopg if not available
try:
    import psycopg2
    PSYCOPG_AVAILABLE = True
    print("Using psycopg2 for PostgreSQL connection")
except ImportError:
    try:
        import psycopg
        psycopg2 = psycopg
        PSYCOPG_AVAILABLE = True
        print("Using psycopg for PostgreSQL connection")
    except ImportError:
        PSYCOPG_AVAILABLE = False
        print("Neither psycopg2 nor psycopg available")

app = Flask(__name__)
CORS(app)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'dbname': os.getenv('DB_NAME', 'campaign_metadata'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'password'),
    'port': os.getenv('DB_PORT', '5432')
}


def get_db_connection():
    """Get database connection"""
    if not PSYCOPG_AVAILABLE:
        raise Exception("psycopg2 not available")

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("Database connection successful with psycopg2!")
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        raise e


def create_cursor(conn):
    """Create a cursor with proper error handling"""
    return conn.cursor()


def detect_date_format(sample_dates):
    """Detect date format from sample dates"""
    if not sample_dates:
        return None

    # Common date formats to try
    formats = [
        '%A, %B %d, %Y',      # Monday, April 07, 2025
        '%Y-%m-%d',           # 2025-04-07
        '%m/%d/%Y',           # 04/07/2025
        '%d/%m/%Y',           # 07/04/2025
        '%B %d, %Y',          # April 07, 2025
    ]

    for fmt in formats:
        matches = 0
        for date_str in sample_dates:
            if safe_date_parsing(date_str, [fmt]):
                matches += 1

        # If more than 50% of dates match this format, use it
        if matches > len(sample_dates) * 0.5:
            print(f"Detected date format: {fmt}")
            return fmt

    print("Could not detect date format, using fallback")
    return None


def get_sample_dates_from_db(table_name, limit=10):
    """Get sample dates from database to detect format"""
    try:
        conn = get_db_connection()
        cursor = create_cursor(conn)
        
        query = f"""
        SELECT DISTINCT "Dates"
        FROM campaign_metadata.{table_name}
        WHERE "Dates" IS NOT NULL
        AND "ID" >= 8000
        AND "Dates" LIKE '%, %%, %'
        LIMIT %s
        """

        cursor.execute(query, (limit,))
        results = cursor.fetchall()
        sample_dates = [row[0] for row in results]

        cursor.close()
        conn.close()

        return sample_dates
    except Exception as e:
        print(f"Error getting sample dates from {table_name}: {e}")
        return []


def generate_date_conditions(start_date, end_date, detected_format=None):
    """Generate date conditions based on detected format or fallback formats"""
    date_conditions = []
    current_date = start_date

    # Use the correct format for the database: "Monday, September 22, 2025"
    target_format = '%A, %B %d, %Y'

    while current_date <= end_date:
        try:
            formatted_date = current_date.strftime(target_format)
            date_conditions.append(f'"Dates" = \'{formatted_date}\'')
        except ValueError:
            print(f"Error formatting date {current_date}")
        current_date = current_date.replace(day=current_date.day + 1)

    return date_conditions


def build_date_filtered_query(table, start_date, end_date):
    """Build query with flexible date filtering"""
    try:
        # Get sample dates to detect format
        sample_dates = get_sample_dates_from_db(table)
        detected_format = detect_date_format(sample_dates)

        # Generate date conditions
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        date_conditions = generate_date_conditions(
            start_dt, end_dt, detected_format)

        print(f"DEBUG: Date conditions for {table}: {date_conditions}")

        if date_conditions:
            date_where_clause = ' OR '.join(date_conditions)
            result = f" AND ({date_where_clause})"
            print(f"DEBUG: Generated date filter for {table}: {result}")
            return result
        else:
            print(f"Warning: No date conditions generated for {table}")
            return ""
    except Exception as e:
        print(f"Error building date filter for {table}: {e}")
        return ""


def safe_date_parsing(date_string, formats):
    """Safely parse date string with multiple formats"""
    for fmt in formats:
        try:
            datetime.strptime(date_string, fmt)
            return True
        except ValueError:
            continue
    return False


def get_inventory_summary(start_date=None, end_date=None):
    """Get summary statistics for inventory with optional date filtering"""
    try:
        conn = get_db_connection()
        cursor = create_cursor(conn)

        # Define brand tables
        brand_tables = [
            ('aa_inventory', 'AA'),
            ('bob_inventory', 'BG'),
            ('cfo_inventory', 'CFO'),
            ('gt_inventory', 'GT'),
            ('hrd_inventory', 'HRD'),
            ('cz_inventory', 'CZ')
        ]

        summary = {
            'total_slots': 0,
            'booked': 0,
            'available': 0,
            'on_hold': 0,
            'by_brand': {}
        }

        for table, brand_code in brand_tables:
            # Build base query with duplicate handling
            base_query = f"""
            WITH latest_slots AS (
                SELECT DISTINCT ON ("ID") *
                FROM campaign_metadata.{table}
                WHERE "ID" >= 8000
                ORDER BY "ID", last_updated DESC
            )
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN "Booked/Not Booked" = 'Booked' THEN 1 END) as booked,
                COUNT(CASE WHEN "Booked/Not Booked" = 'Not Booked' THEN 1 END) as available,
                COUNT(CASE WHEN "Booked/Not Booked" IN ('Hold', 'Hold ', 'hold', 'On hold') THEN 1 END) as on_hold
            FROM latest_slots
            """

            # Add date filtering if provided
            if start_date and end_date:
                # Use dynamic date filtering
                date_filter = build_date_filtered_query(
                    table, start_date, end_date)
                query = base_query + date_filter
                print(f"DEBUG: Query with date filter for {table}: {query}")
            else:
                # No date filtering
                query = base_query
                print(f"DEBUG: Query without date filter for {table}: {query}")

            try:
                cursor.execute(query)
                result = cursor.fetchone()

                if result:
                    brand_total = result[0]
                    brand_booked = result[1]
                    brand_available = result[2]
                    brand_on_hold = result[3]

                    summary['total_slots'] += brand_total
                    summary['booked'] += brand_booked
                    summary['available'] += brand_available
                    summary['on_hold'] += brand_on_hold

                    summary['by_brand'][brand_code] = {
                        'total': brand_total,
                        'booked': brand_booked,
                        'available': brand_available,
                        'on_hold': brand_on_hold,
                        'percentage': round(
                            (brand_booked / brand_total *
                             100) if brand_total > 0 else 0,
                            1)
                    }
            except Exception as e:
                print(f"Error getting summary for {table}: {e}")
                continue

        cursor.close()
        conn.close()

        return summary

    except Exception as e:
        print(f"Error getting inventory summary: {e}")
        return {
            'total_slots': 0,
            'booked': 0,
            'available': 0,
            'on_hold': 0,
            'by_brand': {}
        }


def get_form_submissions_for_week(start_date, end_date):
    """Get form submissions count for each brand for the given week from data_products.sponsorship_bookings_form_submissions"""
    try:
        conn = get_db_connection()
        cursor = create_cursor(conn)

        # Query the real form submissions table
        cursor.execute("""
        SELECT
                brand,
                COUNT(*) as form_count
            FROM data_products.sponsorship_bookings_form_submissions
            WHERE submit_timestamp >= %s
            AND submit_timestamp <= %s
            AND brand IN ('AA', 'BG', 'CFO', 'GT', 'HRD', 'CZ')
            GROUP BY brand
        """, (start_date, end_date))

        results = cursor.fetchall()
        form_submissions = {}

        for row in results:
            form_submissions[row[0]] = row[1]

        print(
            f"Found form submissions from data_products.sponsorship_bookings_form_submissions: {form_submissions}")

        cursor.close()
        conn.close()

        # Ensure all brands have a value (default to 0 if not found)
        for brand_code in ['AA', 'BG', 'CFO', 'GT', 'HRD', 'CZ']:
            if brand_code not in form_submissions:
                form_submissions[brand_code] = 0

        print(
            f"Final form submissions for week {start_date} to {end_date}: {form_submissions}")
        return form_submissions

    except Exception as e:
        print(
            f"Error getting form submissions from data_products.sponsorship_bookings_form_submissions: {e}")
        # Return mock data as fallback
        return {
            'AA': 12,
            'BG': 8,
            'CFO': 15,
            'GT': 6,
            'HRD': 9,
            'CZ': 11
        }


@app.route('/')
def index():
    """Serve the main dashboard"""
    try:
        with open('index.html', 'r') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        return "Dashboard file not found", 404


@app.route('/api/inventory')
def api_inventory():
    """API endpoint for inventory data with filtering"""
    try:
        # Get query parameters
        limit = request.args.get('limit', 100, type=int)
        brand = request.args.get('brand')
        status = request.args.get('status')
        client = request.args.get('client')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        conn = get_db_connection()
        cursor = create_cursor(conn)

        # Define brand tables
        brand_tables = [
            ('aa_inventory', 'AA'),
            ('bob_inventory', 'BG'),
            ('cfo_inventory', 'CFO'),
            ('gt_inventory', 'GT'),
            ('hrd_inventory', 'HRD'),
            ('cz_inventory', 'CZ')
        ]

        all_slots = []

        for table, brand_code in brand_tables:
            # Skip if brand filter is specified and doesn't match
            if brand and brand != brand_code:
                continue

            # Build query with duplicate handling
            base_query = f"""
            WITH latest_slots AS (
                SELECT DISTINCT ON ("ID") *
                FROM campaign_metadata.{table}
                WHERE "ID" >= 8000
                ORDER BY "ID", last_updated DESC
            )
        SELECT
                "ID",
                "Website_Name",
                "Booked/Not Booked",
                "Dates",
                "Client",
                "Booking ID",
                "Product",
                "Price",
                "last_updated"
            FROM latest_slots
            WHERE 1=1
            """

            params = []

            # Add status filter
            if status:
                base_query += ' AND "Booked/Not Booked" = %s'
                params.append(status)

            # Add client filter
            if client:
                base_query += ' AND "Client" ILIKE %s'
                params.append(f'%{client}%')

            # Add date filter
            if start_date and end_date:
                date_filter = build_date_filtered_query(
                    table, start_date, end_date)
                base_query += date_filter

            base_query += f' ORDER BY "ID" LIMIT {limit}'

            try:
                cursor.execute(base_query, params)
                results = cursor.fetchall()

                for row in results:
                    all_slots.append({
                        'id': row[0],
                        'website_name': row[1],
                        'status': row[2],
                        'dates': row[3],
                        'client': row[4],
                        'booking_id': row[5],
                        'product': row[6],
                        'price': row[7],
                        'last_updated': row[8].isoformat() if row[8] else None,
                        'brand': brand_code
                    })
            except Exception as e:
                print(f"Error getting data from {table}: {e}")
                continue

        cursor.close()
        conn.close()

        return jsonify(all_slots)

    except Exception as e:
        print(f"Inventory API Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/brand-overview')
def api_brand_overview():
    """API endpoint for brand overview data"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        summary = get_inventory_summary(start_date, end_date)

        # Format data for frontend
        brand_data = []
        for brand_code, data in summary['by_brand'].items():
            brand_data.append({
                'brand': brand_code,
                'total': data['total'],
                'booked': data['booked'],
                'available': data['available'],
                'on_hold': data['on_hold'],
                'percentage': data['percentage']
            })

        return jsonify(brand_data)

    except Exception as e:
        print(f"Brand Overview API Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/weekly-comparison')
def api_weekly_comparison():
    """API endpoint for weekly comparison data"""
    try:
        # Get current week's data
        today = datetime.now()
        # Get Monday of current week
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)

        # Format dates for display
        week_range = f"{monday.strftime('%b %d, %Y')} to {sunday.strftime('%b %d, %Y')}"

        # Get inventory summary for current week with date filtering
        summary = get_inventory_summary(
            start_date=monday.strftime('%Y-%m-%d'),
            end_date=sunday.strftime('%Y-%m-%d')
        )

        # Get form submissions from database
        form_submissions = get_form_submissions_for_week(monday, sunday)

        # Format data for frontend
        weekly_data = []
        for brand_code, data in summary['by_brand'].items():
            weekly_data.append({
                'brand': brand_code,
                'scheduled': data['booked'],
                'form_submissions': form_submissions.get(brand_code, 0)
            })

        return jsonify({
            'week_range': week_range,
            'data': weekly_data
        })

    except Exception as e:
        print(f"Weekly Comparison API Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/brand-product-breakdown')
def api_brand_product_breakdown():
    """API endpoint for brand product breakdown"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        conn = get_db_connection()
        cursor = create_cursor(conn)
        
        # Define brand tables
        brand_tables = [
            ('aa_inventory', 'AA'),
            ('bob_inventory', 'BG'),
            ('cfo_inventory', 'CFO'),
            ('gt_inventory', 'GT'),
            ('hrd_inventory', 'HRD'),
            ('cz_inventory', 'CZ')
        ]
        
        breakdown_data = {}
        
        for table, brand_code in brand_tables:
            # Build query with duplicate handling
            base_query = f"""
            WITH latest_slots AS (
                SELECT DISTINCT ON ("ID") *
                FROM campaign_metadata.{table}
                WHERE "ID" >= 8000
                ORDER BY "ID", last_updated DESC
            )
                SELECT 
                "Product",
                COUNT(*) as total,
                COUNT(CASE WHEN "Booked/Not Booked" = 'Booked' THEN 1 END) as booked,
                COUNT(CASE WHEN "Booked/Not Booked" = 'Not Booked' THEN 1 END) as available,
                COUNT(CASE WHEN "Booked/Not Booked" IN ('Hold', 'Hold ', 'hold', 'On hold') THEN 1 END) as on_hold
            FROM latest_slots
            WHERE "Product" IS NOT NULL
            """

            # Add date filtering if provided
            if start_date and end_date:
                date_filter = build_date_filtered_query(
                    table, start_date, end_date)
                query = base_query + date_filter + ' GROUP BY "Product" ORDER BY total DESC'
            else:
                query = base_query + ' GROUP BY "Product" ORDER BY total DESC'

            try:
                cursor.execute(query)
                results = cursor.fetchall()

                products = []
                for row in results:
                    products.append({
                        'product': row[0],
                        'total': row[1],
                        'booked': row[2],
                        'available': row[3],
                        'on_hold': row[4]
                    })

                breakdown_data[brand_code] = products
                
            except Exception as e:
                print(f"Error getting product breakdown for {table}: {e}")
                breakdown_data[brand_code] = []
        
        cursor.close()
        conn.close()
        
        return jsonify(breakdown_data)
        
    except Exception as e:
        print(f"Brand Product Breakdown API Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/clients')
def api_clients():
    """API endpoint for client data"""
    try:
        conn = get_db_connection()
        cursor = create_cursor(conn)
        
        # Define brand tables
        brand_tables = [
            ('aa_inventory', 'AA'),
            ('bob_inventory', 'BG'),
            ('cfo_inventory', 'CFO'),
            ('gt_inventory', 'GT'),
            ('hrd_inventory', 'HRD'),
            ('cz_inventory', 'CZ')
        ]

        all_clients = set()

        for table, brand_code in brand_tables:
            query = f"""
            WITH latest_slots AS (
                SELECT DISTINCT ON ("ID") *
                FROM campaign_metadata.{table}
                WHERE "ID" >= 8000
                ORDER BY "ID", last_updated DESC
            )
            SELECT DISTINCT "Client"
            FROM latest_slots
            WHERE "Client" IS NOT NULL AND "Client" != ''
            """

            try:
                cursor.execute(query)
                results = cursor.fetchall()
                
                for row in results:
                    all_clients.add(row[0])
            except Exception as e:
                print(f"Error getting clients from {table}: {e}")
                continue
        
        cursor.close()
        conn.close()
        
        return jsonify(sorted(list(all_clients)))
        
    except Exception as e:
        print(f"Clients API Error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
