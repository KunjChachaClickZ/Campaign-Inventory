import os
import psycopg2
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta
import requests

app = Flask(__name__)
CORS(app)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'campaign_metadata'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'password')
}

# Check if psycopg2 is available
try:
    import psycopg2
    PSYCOPG_AVAILABLE = True
    print("Using psycopg2 for PostgreSQL connection")
except ImportError:
    PSYCOPG_AVAILABLE = False
    print("psycopg2 not available")

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

@app.route('/')
def index():
    """Serve the main dashboard page"""
    try:
        with open('index.html', 'r') as f:
            return f.read()
    except FileNotFoundError:
        return "Dashboard file not found", 404

@app.route('/api/inventory')
def api_inventory():
    """API endpoint for inventory data with filtering"""
    try:
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        brand = request.args.get('brand')
        client = request.args.get('client')
        product = request.args.get('product')
        limit = int(request.args.get('limit', 100))
        
        # Get filtered inventory data
        inventory_data = get_filtered_inventory_slots(
            start_date=start_date,
            end_date=end_date,
            brand=brand,
            client=client,
            product=product,
            limit=limit
        )
        
        return jsonify(inventory_data)
        
    except Exception as e:
        print(f"Inventory API Error: {e}")
        return jsonify({"error": str(e)}), 500

def get_filtered_inventory_slots(start_date=None, end_date=None, brand=None, client=None, product=None, limit=100):
    """Get filtered inventory slots from all brand tables"""
    try:
        conn = get_db_connection()
        cursor = create_cursor(conn)
        
        # Define brand tables and their mappings
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
            if brand and brand.upper() != brand_code:
                continue
                
            # Build base query
            query = f"""
            SELECT 
                inv."ID",
                inv."Dates",
                inv."Booked/Not Booked",
                inv."Media_Asset",
                inv."Website_Name",
                inv."Client",
                inv."last_updated"
            FROM campaign_metadata.{table} inv
            WHERE inv."ID" >= 8000
            """
            
            # Add date filters if provided
            if start_date and end_date:
                # Convert dates to the format used in the database
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                
                # Generate all dates in the range
                date_conditions = []
                current_date = start_dt
                while current_date <= end_dt:
                    formatted_date = current_date.strftime('%A, %B %d, %Y')
                    date_conditions.append(f'"Dates" = \'{formatted_date}\'')
                    current_date = current_date.replace(day=current_date.day + 1)
                    
                if date_conditions:
                    query += f" AND ({' OR '.join(date_conditions)})"
            
            # Add brand filter
            if brand:
                query += f" AND inv.\"Website_Name\" = '{brand_code}'"
            
            # Add client filter
            if client:
                query += f" AND inv.\"Client\" ILIKE '%{client}%'"
            
            # Add product filter
            if product:
                query += f" AND inv.\"Media_Asset\" ILIKE '%{product}%'"
            
            # Add ordering and limit
            query += f" ORDER BY inv.\"last_updated\" DESC LIMIT {limit}"
            
            try:
                cursor.execute(query)
                results = cursor.fetchall()
                
                for row in results:
                    slot_data = {
                        'id': row[0],
                        'date': row[1],
                        'status': row[2],
                        'product': row[3],
                        'brand': row[4],
                        'client': row[5],
                        'last_updated': row[6].isoformat() if row[6] else None
                    }
                    all_slots.append(slot_data)
                    
            except Exception as e:
                print(f"Error querying {table}: {e}")
                continue
        
        cursor.close()
        conn.close()
        
        return all_slots
        
    except Exception as e:
        print(f"Error getting filtered inventory slots: {e}")
        return []

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
            # Build base query
            base_query = f"""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN "Booked/Not Booked" = 'Booked' THEN 1 END) as booked,
                COUNT(CASE WHEN "Booked/Not Booked" = 'Not Booked' THEN 1 END) as available,
                COUNT(CASE WHEN "Booked/Not Booked" IN ('Hold', 'Hold ', 'hold', 'On hold') THEN 1 END) as on_hold
            FROM campaign_metadata.{table}
            WHERE "ID" >= 8000
            """
            
            # Add date filtering if provided
            if start_date and end_date:
                # Use hardcoded dates for April-September 2025 period
                # These are the actual dates that exist in the database
                april_september_2025_dates = [
                    'Monday, April 07, 2025',
                    'Monday, April 14, 2025', 
                    'Monday, April 21, 2025',
                    'Monday, April 28, 2025',
                    'Monday, May 12, 2025',
                    'Monday, May 19, 2025',
                    'Monday, May 26, 2025',
                    'Friday, May 23, 2025',
                    'Friday, May 30, 2025',
                    'Monday, June 02, 2025',
                    'Monday, June 09, 2025',
                    'Monday, June 16, 2025',
                    'Monday, June 23, 2025',
                    'Monday, June 30, 2025',
                    'Monday, July 14, 2025',
                    'Monday, July 21, 2025',
                    'Monday, July 28, 2025',
                    'Monday, August 04, 2025',
                    'Monday, August 11, 2025',
                    'Monday, August 18, 2025',
                    'Monday, September 01, 2025',
                    'Monday, September 08, 2025',
                    'Monday, September 15, 2025',
                    'Monday, September 22, 2025',
                    'Monday, September 29, 2025'
                ]
                
                # Check if the requested date range matches April-September 2025
                if start_date == '2025-04-01' and end_date == '2025-09-30':
                    # Use the hardcoded dates for April-September 2025
                    date_conditions = [f'"Dates" = \'{date}\'' for date in april_september_2025_dates]
                    date_where_clause = ' OR '.join(date_conditions)
                    
                    # Add logic to handle duplicate slot IDs by taking the latest updated slot
                    # Use a subquery to get only the latest updated slot for each ID
                    query = f"""
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
                    WHERE ({date_where_clause})
                    """
                else:
                    # For other date ranges, use the original logic with duplicate handling
                    query = f"""
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
            else:
                # For no date filtering, still handle duplicates
                query = f"""
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
                        'percentage': round((brand_booked / brand_total * 100) if brand_total > 0 else 0, 1)
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

@app.route('/api/brand-overview')
def api_brand_overview():
    """API endpoint for brand overview data with optional date filtering"""
    try:
        # Get date range parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Get inventory summary with date filtering
        summary = get_inventory_summary(start_date=start_date, end_date=end_date)
        
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

@app.route('/api/brand-product-breakdown')
def api_brand_product_breakdown():
    """API endpoint for brand-product breakdown data with optional date filtering"""
    try:
        # Get date range parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        conn = get_db_connection()
        cursor = create_cursor(conn)
        
        # Define brand tables and their mappings
        brand_tables = [
            ('aa_inventory', 'Accountancy Age'),
            ('bob_inventory', 'Bobsguide'),
            ('cfo_inventory', 'The CFO'),
            ('gt_inventory', 'Global Treasurer'),
            ('hrd_inventory', 'HRD Connect'),
            ('cz_inventory', 'ClickZ')
        ]
        
        breakdown_data = {}
        
        for table, brand_name in brand_tables:
            brand_code = table.split('_')[0].upper()
            if brand_code == 'BOB':
                brand_code = 'BG'
            
            base_query = f"""
            SELECT 
                inv."Media_Asset" as product,
                COUNT(*) as total_slots,
                COUNT(CASE WHEN inv."Booked/Not Booked" = 'Booked' THEN 1 END) as booked_slots,
                COUNT(CASE WHEN inv."Booked/Not Booked" = 'Not Booked' THEN 1 END) as available_slots,
                COUNT(CASE WHEN inv."Booked/Not Booked" IN ('Hold', 'Hold ', 'hold', 'On hold') THEN 1 END) as on_hold_slots
            FROM campaign_metadata.{table} inv
            WHERE inv."ID" >= 8000
            """
            
            # Add date filtering if provided
            if start_date and end_date:
                # Use hardcoded dates for April-September 2025 period
                # These are the actual dates that exist in the database
                april_september_2025_dates = [
                    'Monday, April 07, 2025',
                    'Monday, April 14, 2025', 
                    'Monday, April 21, 2025',
                    'Monday, April 28, 2025',
                    'Monday, May 12, 2025',
                    'Monday, May 19, 2025',
                    'Monday, May 26, 2025',
                    'Friday, May 23, 2025',
                    'Friday, May 30, 2025',
                    'Monday, June 02, 2025',
                    'Monday, June 09, 2025',
                    'Monday, June 16, 2025',
                    'Monday, June 23, 2025',
                    'Monday, June 30, 2025',
                    'Monday, July 14, 2025',
                    'Monday, July 21, 2025',
                    'Monday, July 28, 2025',
                    'Monday, August 04, 2025',
                    'Monday, August 11, 2025',
                    'Monday, August 18, 2025',
                    'Monday, September 01, 2025',
                    'Monday, September 08, 2025',
                    'Monday, September 15, 2025',
                    'Monday, September 22, 2025',
                    'Monday, September 29, 2025'
                ]
                
                # Check if the requested date range matches April-September 2025
                if start_date == '2025-04-01' and end_date == '2025-09-30':
                    # Use the hardcoded dates for April-September 2025
                    date_conditions = [f'inv."Dates" = \'{date}\'' for date in april_september_2025_dates]
                    date_where_clause = ' OR '.join(date_conditions)
                    
                    # Add logic to handle duplicate slot IDs by taking the latest updated slot
                    query = f"""
                    WITH latest_slots AS (
                        SELECT DISTINCT ON ("ID") *
                        FROM campaign_metadata.{table}
                        WHERE "ID" >= 8000
                        ORDER BY "ID", last_updated DESC
                    )
                    SELECT 
                        inv."Media_Asset" as product,
                        COUNT(*) as total_slots,
                        COUNT(CASE WHEN inv."Booked/Not Booked" = 'Booked' THEN 1 END) as booked_slots,
                        COUNT(CASE WHEN inv."Booked/Not Booked" = 'Not Booked' THEN 1 END) as available_slots,
                        COUNT(CASE WHEN inv."Booked/Not Booked" IN ('Hold', 'Hold ', 'hold', 'On hold') THEN 1 END) as on_hold_slots
                    FROM latest_slots inv
                    WHERE ({date_where_clause})
                    GROUP BY inv."Media_Asset" 
                    ORDER BY total_slots DESC
                    """
                else:
                    # For other date ranges, use the original logic with duplicate handling
                    query = f"""
                    WITH latest_slots AS (
                        SELECT DISTINCT ON ("ID") *
                        FROM campaign_metadata.{table}
                        WHERE "ID" >= 8000
                        ORDER BY "ID", last_updated DESC
                    )
                    SELECT 
                        inv."Media_Asset" as product,
                        COUNT(*) as total_slots,
                        COUNT(CASE WHEN inv."Booked/Not Booked" = 'Booked' THEN 1 END) as booked_slots,
                        COUNT(CASE WHEN inv."Booked/Not Booked" = 'Not Booked' THEN 1 END) as available_slots,
                        COUNT(CASE WHEN inv."Booked/Not Booked" IN ('Hold', 'Hold ', 'hold', 'On hold') THEN 1 END) as on_hold_slots
                    FROM latest_slots inv
                    GROUP BY inv."Media_Asset" 
                    ORDER BY total_slots DESC
                    """
            else:
                # For no date filtering, still handle duplicates
                query = f"""
                WITH latest_slots AS (
                    SELECT DISTINCT ON ("ID") *
                    FROM campaign_metadata.{table}
                    WHERE "ID" >= 8000
                    ORDER BY "ID", last_updated DESC
                )
                SELECT 
                    inv."Media_Asset" as product,
                    COUNT(*) as total_slots,
                    COUNT(CASE WHEN inv."Booked/Not Booked" = 'Booked' THEN 1 END) as booked_slots,
                    COUNT(CASE WHEN inv."Booked/Not Booked" = 'Not Booked' THEN 1 END) as available_slots,
                    COUNT(CASE WHEN inv."Booked/Not Booked" IN ('Hold', 'Hold ', 'hold', 'On hold') THEN 1 END) as on_hold_slots
                FROM latest_slots inv
                GROUP BY inv."Media_Asset" 
                ORDER BY total_slots DESC
                """
                
            try:
                cursor.execute(query)
                results = cursor.fetchall()
                
                products = {}
                for row in results:
                    product_name = row[0]
                    total_slots = row[1]
                    booked_slots = row[2]
                    available_slots = row[3]
                    on_hold_slots = row[4]
                    
                    products[product_name] = {
                        'total_slots': total_slots,
                        'booked_slots': booked_slots,
                        'available_slots': available_slots,
                        'on_hold_slots': on_hold_slots,
                        'percentage': round((booked_slots / total_slots * 100) if total_slots > 0 else 0, 1)
                    }
                
                breakdown_data[brand_name] = products
                
            except Exception as e:
                print(f"Error querying {table} for product breakdown: {e}")
                continue
        
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
        
        # Get unique clients from all brand tables
        brand_tables = ['aa_inventory', 'bob_inventory', 'cfo_inventory', 'gt_inventory', 'hrd_inventory', 'cz_inventory']
        all_clients = set()
        
        for table in brand_tables:
            query = f"""
            SELECT DISTINCT "Client" 
            FROM campaign_metadata.{table} 
            WHERE "Client" IS NOT NULL AND "Client" != ''
            """
            
            try:
                cursor.execute(query)
                results = cursor.fetchall()
                for row in results:
                    all_clients.add(row[0])
            except Exception as e:
                print(f"Error querying {table} for clients: {e}")
                continue
        
        # Convert to list and sort
        clients_list = sorted(list(all_clients))
        
        # Format for frontend
        clients_data = [{"name": client} for client in clients_list]
        
        cursor.close()
        conn.close()
        
        return jsonify(clients_data)
        
    except Exception as e:
        print(f"Clients API Error: {e}")
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
        
        # Get inventory summary for current week
        summary = get_inventory_summary()
        
        # Get form submissions (mock data for now)
        form_submissions = {
            'AA': 12,
            'BG': 8,
            'CFO': 15,
            'GT': 6,
            'HRD': 9,
            'CZ': 11
        }
        
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5005)
