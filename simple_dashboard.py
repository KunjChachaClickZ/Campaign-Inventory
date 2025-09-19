# Import required libraries
import os
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import json
from datetime import datetime, timedelta
import threading
import time

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Import psycopg2 for PostgreSQL connection
try:
    import psycopg2
    PSYCOPG_AVAILABLE = True
    print("Using psycopg2 for PostgreSQL connection")
except ImportError as e:
    print(f"Error: psycopg2 not available: {e}")
    PSYCOPG_AVAILABLE = False

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'contentive-warehouse-instance-1.cq8sion7djdk.eu-west-2.rds.amazonaws.com'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'analytics'),
    'user': os.getenv('DB_USER', 'kunj.chacha@contentive.com'),
    'password': os.getenv('DB_PASSWORD', '(iRFw989b{5h')
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

# Main route - serve the dashboard
@app.route('/')
def index():
    """Serve the main dashboard page"""
    try:
        with open('index.html', 'r') as f:
            return f.read()
    except FileNotFoundError:
        return "Dashboard file not found", 404

# API endpoint for inventory data
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
        
        all_inventory = []
        
        for table, brand_code in brand_tables:
            # Build the base query
            query = f"""
            SELECT DISTINCT ON (inv."ID")
                inv."ID" as slot_id,
                inv."Dates" as slot_date,
                inv."Booked/Not Booked" as status,
                inv."Booking ID" as booking_id,
                inv."Media_Asset" as product,
                '{brand_code}' as brand,
                COALESCE(cl."Client Name", 'No Client') as client_name,
                COALESCE(cl."Contract ID", 'N/A') as contract_id
            FROM campaign_metadata.{table} inv
            LEFT JOIN campaign_metadata.campaign_ledger cl 
                ON inv."Booking ID" = cl."Booking ID" 
                    AND cl."Brand" = '{brand_code}'
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
                query += f" AND '{brand_code}' = '{brand}'"
            
            # Add client filter
            if client:
                query += f" AND cl.\"Client Name\" ILIKE '%{client}%'"
            
            # Add product filter
            if product:
                query += f" AND inv.\"Media_Asset\" ILIKE '%{product}%'"
            
            # Add ordering and limit
            query += """
                ORDER BY inv."ID", 
                    CASE 
                        WHEN inv."Booked/Not Booked" = 'Booked' THEN 1
                        WHEN inv."Booked/Not Booked" = 'Hold' THEN 2
                        WHEN inv."Booked/Not Booked" = 'Hold ' THEN 2
                        WHEN inv."Booked/Not Booked" = 'hold' THEN 2
                        WHEN inv."Booked/Not Booked" = 'On hold' THEN 2
                        ELSE 3
                    END, inv."Dates" DESC
                LIMIT %s
            """
            
            try:
                cursor.execute(query, (limit,))
                results = cursor.fetchall()
                
                for row in results:
                    all_inventory.append({
                        'slot_id': row[0],
                        'slot_date': row[1],
                        'status': row[2],
                        'booking_id': row[3],
                        'product': row[4],
                        'brand': row[5],
                        'client_name': row[6],
                        'contract_id': row[7]
                    })
                    
            except Exception as e:
                print(f"Error querying {table}: {e}")
                continue
        
        cursor.close()
        conn.close()
        
        return all_inventory
        
    except Exception as e:
        print(f"Error getting inventory data: {e}")
        return []

def get_inventory_summary():
    """Get summary statistics for inventory"""
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
            query = f"""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN "Booked/Not Booked" = 'Booked' THEN 1 END) as booked,
                COUNT(CASE WHEN "Booked/Not Booked" = 'Not Booked' THEN 1 END) as available,
                COUNT(CASE WHEN "Booked/Not Booked" IN ('Hold', 'Hold ', 'hold', 'On hold') THEN 1 END) as on_hold
            FROM campaign_metadata.{table}
            WHERE "ID" >= 8000
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

# API endpoint for overview data
@app.route('/api/overview')
def api_overview():
    """API endpoint for overview data"""
    try:
        summary = get_inventory_summary()
        return jsonify(summary)
        
    except Exception as e:
        print(f"Overview API Error: {e}")
        return jsonify({"error": str(e)}), 500

# API endpoint for brand overview data
@app.route('/api/brand-overview')
def api_brand_overview():
    """API endpoint for brand overview data"""
    try:
        summary = get_inventory_summary()
        
        # Format data for brand overview
        brand_data = []
        for brand_code, data in summary['by_brand'].items():
            brand_data.append({
                'brand': brand_code,
                'percentage': data['percentage'],
                'booked': data['booked'],
                'total': data['total'],
                'available': data['available']
            })
        
        # Sort by percentage descending
        brand_data.sort(key=lambda x: x['percentage'], reverse=True)
        
        return jsonify(brand_data)
        
    except Exception as e:
        print(f"Brand Overview API Error: {e}")
        return jsonify({"error": str(e)}), 500

# API endpoint for clients data
@app.route('/api/clients')
def api_clients():
    """API endpoint for clients data"""
    try:
        conn = get_db_connection()
        cursor = create_cursor(conn)
        
        # Get clients from campaign_ledger
        query = """
        SELECT 
            "Client Name" as client_name,
            COUNT(DISTINCT "Booking ID") as total_bookings,
            STRING_AGG(DISTINCT "Brand", ', ') as brands
        FROM campaign_metadata.campaign_ledger
        WHERE "Client Name" IS NOT NULL 
            AND "Client Name" != ''
            AND "Booking ID" IS NOT NULL
            AND "Booking ID" != ''
        GROUP BY "Client Name"
        ORDER BY total_bookings DESC
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        clients = []
        for row in results:
            clients.append({
                'client_name': row[0],
                'total_bookings': row[1],
                'brands': row[2].split(', ') if row[2] else []
            })
        
        cursor.close()
        conn.close()
        
        return jsonify(clients)
        
    except Exception as e:
        print(f"Clients API Error: {e}")
        return jsonify({"error": str(e)}), 500

# API endpoint for weekly comparison
@app.route('/api/weekly-comparison')
def api_weekly_comparison():
    """API endpoint for weekly comparison between booked data and form submissions"""
    try:
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date or not end_date:
            return jsonify({"error": "start_date and end_date parameters are required"}), 400
        
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
        
        date_where_clause = ' OR '.join(date_conditions)
        
        # Get inventory data directly from database
        conn = get_db_connection()
        cursor = create_cursor(conn)
        
        # Query all brand tables for scheduled slots
        all_brands = ['aa_inventory', 'bob_inventory', 'cfo_inventory', 'gt_inventory', 'hrd_inventory', 'cz_inventory']
        inventory_bookings = []
        
        for table in all_brands:
            brand_code = table.split('_')[0].upper()
            if brand_code == 'BOB':
                brand_code = 'BG'
            
            query = f"""
            SELECT DISTINCT ON (inv."Booking ID")
                inv."Booking ID" as booking_id,
                '{brand_code}' as brand,
                COALESCE(cl."Client Name", 'No Client') as client_name,
                inv."Dates" as slot_date
            FROM campaign_metadata.{table} inv
            LEFT JOIN campaign_metadata.campaign_ledger cl 
                ON inv."Booking ID" = cl."Booking ID" 
                    AND cl."Brand" = '{brand_code}'
            WHERE inv."ID" >= 8000
                AND ({date_where_clause})
                AND inv."Booking ID" IS NOT NULL 
                AND inv."Booking ID" != ''
                AND (inv."Booked/Not Booked" = 'Booked' 
                     OR inv."Booked/Not Booked" = 'Hold' 
                     OR inv."Booked/Not Booked" = 'Hold ' 
                     OR inv."Booked/Not Booked" = 'hold' 
                     OR inv."Booked/Not Booked" = 'On hold')
            ORDER BY inv."Booking ID"
            """
            
            try:
                cursor.execute(query)
                results = cursor.fetchall()
                
                for row in results:
                    inventory_bookings.append({
                        'booking_id': row[0],
                        'brand': row[1],
                        'client_name': row[2],
                        'slot_date': row[3]
                    })
            except Exception as e:
                print(f"Error querying {table}: {e}")
                continue
        
        cursor.close()
        conn.close()
        
        # Get form submissions data for the week
        conn = get_db_connection()
        cursor = create_cursor(conn)
        
        form_query = """
        SELECT 
            booking_id,
            brand,
            product_type,
            start_date,
            end_date,
            client_name
        FROM data_products.sponsorship_bookings_form_submissions
        WHERE start_date >= %s AND end_date <= %s
        """
        
        cursor.execute(form_query, (start_date, end_date))
        form_results = cursor.fetchall()
        
        # Convert form submissions to list of dictionaries
        form_submissions = []
        for row in form_results:
            form_submissions.append({
                'booking_id': row[0],
                'brand': row[1],
                'product_type': row[2],
                'start_date': row[3].isoformat() if row[3] else None,
                'end_date': row[4].isoformat() if row[4] else None,
                'client_name': row[5]
            })
        
        cursor.close()
        conn.close()
        
        # Count scheduled campaigns vs form submissions by brand
        scheduled_by_brand = {}
        form_by_brand = {}
        
        # Count unique scheduled campaigns by booking ID from inventory (source of truth)
        unique_booking_ids = set()
        for booking in inventory_bookings:
            brand = booking.get('brand', 'Unknown')
            booking_id = booking.get('booking_id', '')
            if booking_id and booking_id != 'N/A':
                unique_key = f"{brand}_{booking_id}"
                if unique_key not in unique_booking_ids:
                    unique_booking_ids.add(unique_key)
                    if brand not in scheduled_by_brand:
                        scheduled_by_brand[brand] = 0
                    scheduled_by_brand[brand] += 1
        
        # Count form submissions
        for item in form_submissions:
            brand = item.get('brand', 'Unknown')
            if brand not in form_by_brand:
                form_by_brand[brand] = 0
            form_by_brand[brand] += 1
        
        # Create comparison summary
        comparison_data = {
            'week_range': {
                'start_date': start_date,
                'end_date': end_date
            },
            'summary': {
                'total_scheduled': sum(scheduled_by_brand.values()),
                'total_form_submissions': sum(form_by_brand.values())
            },
            'by_brand': {}
        }
        
        # Combine data by brand
        all_brands = set(scheduled_by_brand.keys()) | set(form_by_brand.keys())
        for brand in all_brands:
            comparison_data['by_brand'][brand] = {
                'scheduled': scheduled_by_brand.get(brand, 0),
                'form_submissions': form_by_brand.get(brand, 0)
            }
        
        return jsonify(comparison_data)
    except Exception as e:
        print(f"Weekly Comparison API Error: {e}")
        return jsonify({"error": str(e)}), 500

# API endpoint for brand product breakdown
@app.route('/api/brand-product-breakdown')
def api_brand_product_breakdown():
    """API endpoint for brand-product breakdown data"""
    try:
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
            
            # Get product breakdown for this brand
            query = f"""
            SELECT 
                inv."Media_Asset" as product,
                COUNT(*) as total_slots,
                COUNT(CASE WHEN inv."Booked/Not Booked" = 'Booked' THEN 1 END) as booked_slots,
                COUNT(CASE WHEN inv."Booked/Not Booked" = 'Not Booked' THEN 1 END) as available_slots,
                COUNT(CASE WHEN inv."Booked/Not Booked" IN ('Hold', 'Hold ', 'hold', 'On hold') THEN 1 END) as on_hold_slots
            FROM campaign_metadata.{table} inv
            WHERE inv."ID" >= 8000
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
                    
                    percentage = round((booked_slots / total_slots * 100) if total_slots > 0 else 0, 1)
                    
                    products[product_name] = {
                        'total_slots': total_slots,
                        'booked_slots': booked_slots,
                        'available_slots': available_slots,
                        'on_hold_slots': on_hold_slots,
                        'percentage': percentage
                    }
                
                breakdown_data[brand_name] = products
                
            except Exception as e:
                print(f"Error getting breakdown for {table}: {e}")
                breakdown_data[brand_name] = {}
                continue
        
        cursor.close()
        conn.close()
        
        return jsonify(breakdown_data)
        
    except Exception as e:
        print(f"Brand Product Breakdown API Error: {e}")
        return jsonify({"error": str(e)}), 500

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5005)
