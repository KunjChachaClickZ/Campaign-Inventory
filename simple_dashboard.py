from flask import Flask, render_template_string, jsonify, request
from datetime import datetime, timedelta
from flask_cors import CORS
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import psycopg2 for PostgreSQL connection
try:
    import psycopg2
    PSYCOPG_AVAILABLE = True
    print("Using psycopg2 for PostgreSQL connection")
except ImportError as e:
    print(f"Error: psycopg2 not available: {e}")
    try:
        # Fallback to psycopg2-binary
        import psycopg2
        PSYCOPG_AVAILABLE = True
        print("Using psycopg2-binary as fallback")
    except ImportError as e2:
        print(f"Error: psycopg2-binary also not available: {e2}")
        PSYCOPG_AVAILABLE = False

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Database configuration - use environment variables for deployment
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'contentive-warehouse-instance-1.cq8sion7djdk.eu-west-2.rds.amazonaws.com'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'analytics'),  # psycopg2 uses 'database' not 'dbname'
    'user': os.getenv('DB_USER', 'kunj.chacha@contentive.com'),
    'password': os.getenv('DB_PASSWORD', '(iRFw989b{5h')
}

# Alternative: Use DATABASE_URL if provided (Render.com style)
if os.getenv('DATABASE_URL'):
    import urllib.parse
    url = urllib.parse.urlparse(os.getenv('DATABASE_URL'))
    DB_CONFIG = {
        'host': url.hostname,
        'port': url.port or 5432,
        'dbname': url.path[1:],  # Changed from 'database' to 'dbname' for psycopg
        'user': url.username,
        'password': url.password
    }

# Connection pool for better performance
_connection_pool = None
_connection_lock = None

def init_connection_pool():
    """Initialize connection pool"""
    global _connection_pool, _connection_lock
    if _connection_pool is None:
        import threading
        _connection_lock = threading.Lock()
        _connection_pool = []

def get_db_connection():
    """Get database connection with connection pooling"""
    global _connection_pool, _connection_lock

    if not PSYCOPG_AVAILABLE:
        raise Exception("psycopg not available")

    init_connection_pool()

    with _connection_lock:
        # Try to reuse existing connection
        if _connection_pool:
            conn = _connection_pool.pop()
            try:
                # Test if connection is still alive
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                return conn
            except Exception as e:
                # Connection is dead, create new one
                print(f"Connection test failed: {e}")
                pass

        # Create new connection
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            print("Database connection successful with psycopg2!")
            return conn
        except Exception as e:
            print(f"Database connection error: {e}")
            raise e

def return_db_connection(conn):
    """Return connection to pool for reuse"""
    global _connection_pool, _connection_lock
    
    if conn and _connection_pool is not None:
        with _connection_lock:
            if len(_connection_pool) < 5:  # Limit pool size
                _connection_pool.append(conn)
            else:
                conn.close()

def create_cursor(conn):
    """Create a cursor"""
    return conn.cursor()

def execute_query(query, params=None, fetch_all=True):
    """Execute query with automatic connection management"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = create_cursor(conn)
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if fetch_all:
            results = cursor.fetchall()
        else:
            results = cursor.fetchone()
        
        cursor.close()
        return results
        
    except Exception as e:
        print(f"Query execution error: {e}")
        raise e
    finally:
        if conn:
            return_db_connection(conn)

def convert_excel_date_to_readable(date_value):
    """Convert Excel date number or string date to readable format"""
    if date_value is None:
        return ''
    
    try:
        # If it's already a string date, return as is
        if isinstance(date_value, str):
            # Check if it's already a readable date format
            if any(day in date_value for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']):
                return date_value
            # Check if it's a numeric string (Excel date)
            if date_value.isdigit():
                excel_date = int(date_value)
            else:
                return date_value
        else:
            # If it's a number, treat as Excel date
            excel_date = int(date_value)
        
        # Convert Excel date number to datetime
        # Excel dates are days since January 1, 1900
        from datetime import datetime, timedelta
        excel_epoch = datetime(1900, 1, 1)
        actual_date = excel_epoch + timedelta(days=excel_date - 2)  # -2 for Excel's leap year bug
        
        # Format as "Monday, January 06, 2025"
        return actual_date.strftime('%A, %B %d, %Y')
        
    except Exception as e:
        print(f"Error converting date {date_value}: {e}")
        return str(date_value) if date_value else ''

def get_inventory_summary(product_filter=None, brand_filter=None, start_date=None, end_date=None):
    """Get summary of all inventory data with optional filters"""
    conn = get_db_connection()
    cursor = create_cursor(conn)
    
    try:
        # Build base query with filters
        base_where = 'WHERE "ID" >= 8000'
        
        # Add date filter if specified (using the actual "Dates" column format)
        if start_date and end_date:
            try:
                from datetime import datetime, timedelta
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                end_dt = end_dt + timedelta(days=1)
                
                # Generate all dates in the range in the database format
                date_conditions = []
                current_date = start_dt
                while current_date < end_dt:
                    formatted_date = current_date.strftime('%A, %B %d, %Y')
                    date_conditions.append(f'"Dates" = \'{formatted_date}\'')
                    current_date += timedelta(days=1)
                
                if date_conditions:
                    base_where += f" AND ({' OR '.join(date_conditions)})"
            except Exception as e:
                print(f"Error in date filtering for summary: {e}")
        
        # Get summary from all inventory tables - using correct business logic
        # Query all brand tables individually and combine results
        brands_data = []
        
        # Define all brand tables
        brand_tables = {
            'AA': 'aa_inventory',
            'BG': 'bob_inventory', 
            'CFO': 'cfo_inventory',
            'GT': 'gt_inventory',
            'HRD': 'hrd_inventory',
            'CZ': 'cz_inventory'
        }
        
        for brand_code, table_name in brand_tables.items():
            query = f"""
            SELECT
                    '{brand_code}' as brand,
                COUNT(DISTINCT inv."ID") as total_slots,
                COUNT(DISTINCT CASE WHEN inv."Booked/Not Booked" = 'Booked' THEN inv."ID" END) as booked,
                COUNT(DISTINCT CASE WHEN inv."Booked/Not Booked" = 'Not Booked' THEN inv."ID" END) as available,
                    COUNT(DISTINCT CASE WHEN inv."Booked/Not Booked" IN ('Hold', 'Hold ', 'hold', 'On hold', 'On hold ') THEN inv."ID" END) as on_hold
                FROM campaign_metadata.{table_name} inv
                {base_where}
                """

            cursor.execute(query)
            result = cursor.fetchone()

            if result:
                total_slots = result[1] or 0
                booked = result[2] or 0
                available = result[3] or 0
                on_hold = result[4] or 0

                # Calculate percentage
                percentage = (booked / total_slots * 100) if total_slots > 0 else 0

                brands_data.append({
                    'brand': brand_code,
                    'name': brand_code,  # Use brand code as name for now
                    'total_slots': total_slots,
                    'booked': booked,
                    'available': available,
                    'on_hold': on_hold,
                    'percentage': round(percentage, 2)
                })
        
        return brands_data
        
    except Exception as e:
        print(f"Error in get_inventory_summary: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_inventory_by_product_and_brand():
    """Get inventory breakdown by product and brand for default state using individual brand tables"""
    # Use the same approach as get_inventory_summary but return data in the expected format
    try:
        brands_data = get_inventory_summary()
        
        # Convert to the format expected by the dashboard
        processed_results = []
        for brand_data in brands_data:
            if brand_data['total_slots'] > 0:
                processed_results.append({
                    'brand': brand_data['brand'],
                    'product': 'General Inventory',  # Default product name
                    'total_slots': brand_data['total_slots'],
                    'booked': brand_data['booked'],
                    'available': brand_data['available'],
                    'on_hold': brand_data['on_hold'],
                    'unclassified': 0  # Set to 0 since this field doesn't exist in the data
                })
        
        return processed_results
        
    except Exception as e:
        print(f"Error in get_inventory_by_product_and_brand: {e}")
        return []

def parse_slot_id(slot_id_string):
    """Parse slot ID string to extract product, date, week, and slot information"""
    if not slot_id_string:
        return None
    
    try:
        # Example: "Newsletter_Sponsorship_BM-S2_2024_July_Week5_Slot1"
        parts = slot_id_string.split('_')
        
        if len(parts) >= 6:
            # Extract components
            product_type = parts[0]  # Newsletter, Gated_Content, etc.
            product_code = parts[2] if len(parts) > 2 else parts[1]  # BM-S2, LD-1, etc.
            year = parts[3] if len(parts) > 3 else None  # 2024
            month = parts[4] if len(parts) > 4 else None  # July
            week_info = parts[5] if len(parts) > 5 else None  # Week5
            slot_info = parts[6] if len(parts) > 6 else None  # Slot1
            
            # Extract week number and slot number
            week_num = None
            slot_num = None
            
            if week_info and 'Week' in week_info:
                week_num = week_info.replace('Week', '')
            
            if slot_info and 'Slot' in slot_info:
                slot_num = slot_info.replace('Slot', '')
            
            return {
                'product_type': product_type,
                'product_code': product_code,
                'year': year,
                'month': month,
                'week': week_num,
                'slot': slot_num,
                'full_string': slot_id_string
            }
    except Exception as e:
        print(f"Error parsing slot ID {slot_id_string}: {e}")
    
    return None

def get_filtered_inventory_slots(product_filter=None, brand_filter=None, start_date=None, end_date=None, client_filter=None):
    """Get individual inventory slots with client information for filtered results using individual brand tables"""
    conn = get_db_connection()
    cursor = create_cursor(conn)
    
    try:
        # Use individual brand tables instead of the problematic all_inventory view
        all_results = []
        
        # Define brand tables and their mappings
        brand_tables = [
            ('aa_inventory', 'AA'),
            ('bob_inventory', 'BG'),
            ('cfo_inventory', 'CFO'),
            ('gt_inventory', 'GT'),
            ('hrd_inventory', 'HRD'),
            ('cz_inventory', 'CZ')
        ]
        
        for table_name, brand_code in brand_tables:
            # Skip if brand filter is specified and doesn't match
            # Map frontend brand names to database brand codes
            if brand_filter and brand_filter != 'All':
                # Map frontend brand names to database codes
                brand_mapping = {
                    'Accountancy Age': 'AA',
                    'Bobsguide': 'BG', 
                    'The CFO': 'CFO',
                    'Global Treasurer': 'GT',
                    'HRD Connect': 'HRD',
                    'ClickZ': 'CZ'
                }
                expected_brand_code = brand_mapping.get(brand_filter, brand_filter)
                if brand_code != expected_brand_code:
                    continue
                
            # Build query for this brand table with client information from campaign_ledger
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
            FROM campaign_metadata.{table_name} inv
            LEFT JOIN campaign_metadata.campaign_ledger cl 
                ON inv."Booking ID" = cl."Booking ID" 
                AND cl."Brand" = '{brand_code}'
            WHERE inv."ID" >= 8000
            """
            
            # Add date filter if specified - now properly implemented
            if start_date and end_date:
                print(f"Filtering by date range: {start_date} to {end_date}")
                
                # Database stores dates as "Monday, January 06, 2025" format
                # Convert to proper date range filter
                try:
                    from datetime import datetime, timedelta
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                    
                    # Add one day to end_date to include the full day
                    end_dt = end_dt + timedelta(days=1)
                    
                    # Generate all dates in the range in the database format
                    date_conditions = []
                    current_date = start_dt
                    while current_date < end_dt:
                        # Format as "Monday, January 06, 2025"
                        formatted_date = current_date.strftime('%A, %B %d, %Y')
                        date_conditions.append(f'"Dates" = \'{formatted_date}\'')
                        current_date += timedelta(days=1)
                    
                    if date_conditions:
                        query += f" AND ({' OR '.join(date_conditions)})"
                        print(f"Added date filter with {len(date_conditions)} date conditions")
                    
                except Exception as e:
                    print(f"Error in date filtering: {e}")
                    # Fallback: remove date filter to show all data
                    print("Falling back to no date filter")
            
            # Add product filter if specified
            if product_filter:
                # Map frontend product names to database product names
                product_mapping = {
                    'Hosted_Content': 'Hosted_Content',
                    'LVB_Mailshot': 'LVB_Mailshot',
                    'Leading_Voice_Broadcast': 'Leading_Voice_Broadcast',
                    'Mailshot': 'Mailshot',
                    'Newsletter_Category_Sponsorship': 'Newsletter_Category_Sponsorship',
                    'Newsletter_Featured_Placement': 'Newsletter_Featured_Placement',
                    'Newsletter_Sponsorship': 'Newsletter_Sponsorship',
                    'Original_Content_Production': 'Original_Content_Production',
                    'Weekender_Newsletter_Sponsorship': 'Weekender_Newsletter_Sponsorship'
                }
                
                db_product_name = product_mapping.get(product_filter, product_filter)
                query += f" AND inv.\"Media_Asset\" = '{db_product_name}'"
            
            # Add client filter if specified
            if client_filter and client_filter != 'All':
                query += f" AND cl.\"Client Name\" = '{client_filter}'"
            
            # Add ORDER BY clause for DISTINCT ON - prioritize Booked status
            query += """ ORDER BY inv."ID", 
                CASE 
                    WHEN inv."Booked/Not Booked" = 'Booked' THEN 1
                    WHEN inv."Booked/Not Booked" = 'Hold' THEN 2
                    WHEN inv."Booked/Not Booked" = 'Hold ' THEN 2
                    WHEN inv."Booked/Not Booked" = 'hold' THEN 2
                    WHEN inv."Booked/Not Booked" = 'On hold' THEN 2
                    ELSE 3
                END, inv."Dates" DESC"""
            
            print(f"Executing query for {table_name}: {query}")
            cursor.execute(query)
            brand_results = cursor.fetchall()
            print(f"Found {len(brand_results)} results for {table_name}")
            
            # Process results for this brand
            for row in brand_results:
                try:
                    # psycopg returns tuples: (slot_id, slot_date, status, booking_id, product, brand, client_name, contract_id)
                    # Determine status
                    if row[2] == 'Booked':  # status
                        display_status = 'Booked'
                    elif row[2] == 'Hold':  # status
                        display_status = 'On Hold'
                    else:
                        display_status = 'Available'
                    
                    # Create result object matching MCP format
                    all_results.append({
                        'brand': brand_code,
                        'slot_id': row[0] if row[0] is not None else 0,           # slot_id
                        'slot_date': convert_excel_date_to_readable(row[1]),      # slot_date
                        'status': row[2] if row[2] is not None else '',           # status
                        'booking_id': row[3] if row[3] is not None else '',       # booking_id
                        'product': row[4] if row[4] is not None else 'Mailshot',  # product
                        'client_name': row[6] if row[6] is not None else 'No Client',  # client_name
                        'contract_id': row[7] if row[7] is not None else 'N/A'    # contract_id
                    })
                    
                except Exception as e:
                    # Skip problematic records
                    print(f"Skipping problematic record: {e}")
                    continue
        
        print(f"Total results: {len(all_results)}")
        return all_results
        
    except Exception as e:
        print(f"Error in get_filtered_inventory_slots: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_filtered_inventory_by_product(product_filter, brand_filter=None, start_date=None, end_date=None):
    """Get inventory filtered by product using campaign_ledger join"""
    conn = get_db_connection()
    cursor = create_cursor(conn)
    
    try:
        # This function will be implemented to handle product filtering
        # by joining inventory tables with campaign_ledger
        # For now, return basic summary
        return get_inventory_summary(brand_filter, start_date, end_date)
        
    except Exception as e:
        print(f"Error in get_filtered_inventory_by_product: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_upcoming_deliverables():
    """Get upcoming deliverables for next 2 weeks (current week + next week) from campaign ledger"""
    conn = get_db_connection()
    cursor = create_cursor(conn)
    
    try:
        query = """
        SELECT 
            "Client Name" as client,
            "Product Name - As per Listing Hub" as product,
            "Scheduled Live Date" as deliverable_date
        FROM campaign_metadata.campaign_ledger
        WHERE "Scheduled Live Date" >= CURRENT_DATE 
        AND "Scheduled Live Date" <= CURRENT_DATE + INTERVAL '14 days'
        AND "Status" = 'Active'
        ORDER BY "Scheduled Live Date" ASC
        LIMIT 20
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        deliverables = []
        for row in results:
            # psycopg returns tuples: (client, product, deliverable_date)
            deliverables.append({
                'client': row[0],           # client
                'product': row[1],          # product
                'deliverable_date': convert_excel_date_to_readable(row[2])  # deliverable_date
            })
        
        return deliverables
        
    finally:
        cursor.close()
        conn.close()

@app.route('/')
def dashboard():
    """Main dashboard route - serve the enhanced dashboard"""
    try:
        # Serve the enhanced dashboard HTML file
        with open('index.html', 'r') as f:
            return f.read()
    except Exception as e:
        print(f"Error serving dashboard: {e}")
        return f"Error loading dashboard: {str(e)}", 500

@app.route('/api/inventory')
def api_inventory():
    """API endpoint for inventory data with filters"""
    try:
        # Get filter parameters from request
        product_filter = request.args.get('product')
        brand_filter = request.args.get('brand')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        status_filter = request.args.get('status')  # New parameter for status filtering
        client_filter = request.args.get('client')  # New parameter for client filtering
        
        # Always use the filtered inventory slots function for detailed results
        inventory_slots = get_filtered_inventory_slots(
            product_filter=product_filter,
            brand_filter=brand_filter,
            start_date=start_date,
            end_date=end_date,
            client_filter=client_filter
        )
        
        # Apply status filter if specified
        if status_filter:
            if status_filter == 'Booked':
                inventory_slots = [slot for slot in inventory_slots if slot['status'] == 'Booked']
            elif status_filter == 'Available':
                inventory_slots = [slot for slot in inventory_slots if slot['status'] == 'Not Booked']
            elif status_filter == 'On Hold':
                inventory_slots = [slot for slot in inventory_slots if slot['status'] == 'Hold']
        
        return jsonify(inventory_slots)
    except Exception as e:
        print(f"API Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/bookings')
def api_bookings():
    """API endpoint for upcoming deliverables"""
    try:
        upcoming_deliverables = get_upcoming_deliverables()
        return jsonify(upcoming_deliverables)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/campaign-ledger')
def api_campaign_ledger():
    """API endpoint for campaign ledger data"""
    try:
        # Get campaign ledger data from database
        conn = get_db_connection()
        cursor = create_cursor(conn)
        
        # Query campaign ledger data using actual column names from the database
        query = """
        SELECT 
            "ID" as id,
            "Client Name" as client,
            "Product Name - As per Listing Hub" as product,
            "Brand" as brand,
            "Scheduled Live Date" as start_date,
            "Schedule End Date" as end_date,
            "Status" as status
        FROM campaign_metadata.campaign_ledger
        ORDER BY "Scheduled Live Date" DESC
        LIMIT 100
        """
        
        cursor.execute(query)
        campaign_data = cursor.fetchall()
        
        # Convert to list of dictionaries
        result = []
        for row in campaign_data:
            # psycopg returns tuples: (id, client, product, brand, start_date, end_date, status)
            result.append({
                'id': row[0],                                    # id
                'client': row[1],                                # client
                'product': row[2],                               # product
                'brand': row[3],                                 # brand
                'start_date': convert_excel_date_to_readable(row[4]),   # start_date
                'end_date': convert_excel_date_to_readable(row[5]),     # end_date
                'status': row[6]                                 # status
            })
        
        cursor.close()
        conn.close()
        
        return jsonify(result)
    except Exception as e:
        print(f"Campaign Ledger API Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/brand-overview')
def api_brand_overview():
    """API endpoint for brand overview data"""
    try:
        # Get brand overview data
        brands_data = get_inventory_summary()
        
        # Format the data for the frontend - return array format that frontend expects
        result = []
        
        # Proper brand code mapping
        brand_code_mapping = {
            'Accountancy Age': 'AA',
            'Bobsguide': 'BG',
            'The CFO': 'CFO',
            'Global Treasurer': 'GT',
            'HRD Connect': 'HRD',
            'ClickZ': 'CZ'
        }
        
        for brand_data in brands_data:
            brand_name = brand_data['brand']
            brand_code = brand_code_mapping.get(brand_name, brand_name.split()[0][:2].upper())
            
            result.append({
                'brand': brand_code,
                'name': brand_name,
                'total_slots': brand_data['total_slots'],
                'booked': brand_data['booked'],
                'on_hold': brand_data['on_hold'],
                'available': brand_data['available'],
                'percentage': round((brand_data['booked'] / brand_data['total_slots']) * 100) if brand_data['total_slots'] > 0 else 0
            })
        
        return jsonify(result)
    except Exception as e:
        print(f"Brand Overview API Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/current-week-inventory')
def api_current_week_inventory():
    """API endpoint for current week inventory data"""
    try:
        # Get current week data
        today = datetime.now()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        # Format dates for database query
        start_date = start_of_week.strftime('%Y-%m-%d')
        end_date = end_of_week.strftime('%Y-%m-%d')
        
        # Get inventory data for current week
        current_week_data = get_filtered_inventory_slots(
            start_date=start_date,
            end_date=end_date
        )
        
        return jsonify(current_week_data)
    except Exception as e:
        print(f"Current Week Inventory API Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/weekly-form-submissions')
def api_weekly_form_submissions():
    """API endpoint for form submissions data for a specific week"""
    try:
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date or not end_date:
            return jsonify({"error": "start_date and end_date parameters are required"}), 400
        
        # Query form submissions from data_products.sponsorship_bookings_form_submissions
        conn = get_db_connection()
        cursor = create_cursor(conn)
        
        query = """
        SELECT 
            booking_id,
            submit_timestamp,
            email_id,
            brand,
            product_type,
            start_date,
            end_date,
            client_name,
            client_type,
            created_at
        FROM data_products.sponsorship_bookings_form_submissions
        WHERE start_date >= %s AND end_date <= %s
        ORDER BY submit_timestamp DESC
        """
        
        cursor.execute(query, (start_date, end_date))
        results = cursor.fetchall()
        
        # Convert to list of dictionaries
        form_submissions = []
        for row in results:
            form_submissions.append({
                'booking_id': row[0],
                'submit_timestamp': row[1].isoformat() if row[1] else None,
                'email_id': row[2],
                'brand': row[3],
                'product_type': row[4],
                'start_date': row[5].isoformat() if row[5] else None,
                'end_date': row[6].isoformat() if row[6] else None,
                'client_name': row[7],
                'client_type': row[8],
                'created_at': row[9].isoformat() if row[9] else None
            })
        
        cursor.close()
        conn.close()
        
        return jsonify(form_submissions)
    except Exception as e:
        print(f"Weekly Form Submissions API Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/weekly-comparison')
def api_weekly_comparison():
    """API endpoint for weekly comparison between booked data and form submissions"""
    try:
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date or not end_date:
            return jsonify({"error": "start_date and end_date parameters are required"}), 400
        
        # Use the existing inventory API to get booked slots with booking IDs
        # This is simpler and more reliable than creating complex UNION queries
        import requests

        # Get inventory data for the date range
        inventory_url = f"http://localhost:5005/api/inventory?start_date={start_date}&end_date={end_date}&limit=10000"
        try:
            inventory_response = requests.get(inventory_url, timeout=30)
            if inventory_response.status_code == 200:
                all_inventory = inventory_response.json()
                # Filter for only booked/scheduled slots with valid booking IDs
                inventory_bookings = []
                for item in all_inventory:
                    # Include Booked, Hold, hold, On hold as "scheduled"
                    status = item.get('status', '').strip().lower()
                    is_scheduled = (status == 'booked' or
                                   'hold' in status or
                                   'on hold' in status)

                    if (is_scheduled and
                        item.get('booking_id') and
                        item.get('booking_id') not in ['', 'N/A', None]):
                        inventory_bookings.append({
                            'booking_id': item['booking_id'],
                            'brand': item['brand'],
                            'client_name': item.get('client_name', 'No Client'),
                            'slot_date': item['slot_date']
                        })
            else:
                inventory_bookings = []
        except:
            inventory_bookings = []
        
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
            booking_id = booking.get('booking_id', '')  # Using booking_id field
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
        
        for table_name, brand_name in brand_tables:
            try:
                # Query to get product breakdown for this brand
                query = f"""
                SELECT 
                    "Media_Asset" as product,
                    COUNT(DISTINCT "ID") as total_slots,
                    COUNT(DISTINCT CASE WHEN "Booked/Not Booked" = 'Booked' THEN "ID" END) as booked_slots,
                    COUNT(DISTINCT CASE WHEN "Booked/Not Booked" = 'Not Booked' THEN "ID" END) as available_slots,
                    COUNT(DISTINCT CASE WHEN "Booked/Not Booked" = 'Hold' THEN "ID" END) as on_hold_slots
                FROM campaign_metadata.{table_name}
                WHERE "ID" >= 8000 AND "Media_Asset" IS NOT NULL
                GROUP BY "Media_Asset"
                ORDER BY total_slots DESC
                """
                
                cursor.execute(query)
                product_results = cursor.fetchall()
                
                # Process results for this brand
                brand_products = {}
                for row in product_results:
                    product_name = row[0] if row[0] else 'Unknown Product'
                    total_slots = row[1] if row[1] else 0
                    booked_slots = row[2] if row[2] else 0
                    available_slots = row[3] if row[3] else 0
                    on_hold_slots = row[4] if row[4] else 0
                    
                    # Calculate percentage
                    percentage = (booked_slots / total_slots * 100) if total_slots > 0 else 0
                    
                    brand_products[product_name] = {
                        'total_slots': total_slots,
                        'booked_slots': booked_slots,
                        'available_slots': available_slots,
                        'on_hold_slots': on_hold_slots,
                        'percentage': round(percentage, 1)
                    }
                
                breakdown_data[brand_name] = brand_products
                
            except Exception as e:
                print(f"Error querying {table_name}: {e}")
                # Add empty data for this brand if query fails
                breakdown_data[brand_name] = {}
        
        cursor.close()
        conn.close()
        
        return jsonify(breakdown_data)
        
    except Exception as e:
        print(f"Brand Product Breakdown API Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/clients')
def api_clients():
    """API endpoint to get unique client names with actual inventory slot counts"""
    try:
        conn = get_db_connection()
        cursor = create_cursor(conn)
        
        # Simple query to get unique clients from campaign ledger
        query = """
        SELECT DISTINCT 
            TRIM("Client Name") as client_name,
            COUNT(*) as booking_count,
            STRING_AGG(DISTINCT "Brand", ', ' ORDER BY "Brand") as brands
        FROM campaign_metadata.campaign_ledger 
        WHERE "Client Name" IS NOT NULL 
        AND "Client Name" != '' 
        AND TRIM("Client Name") != ''
        GROUP BY TRIM("Client Name")
        ORDER BY booking_count DESC, client_name
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Process results to create client list
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

@app.route('/api/weekly-overview')
def api_weekly_overview():
    """API endpoint for weekly overview data"""
    try:
        # Get current week's data
        from datetime import datetime, timedelta
        
        # Use January 6-12, 2025 as our sample week (where we have data)
        week_start = datetime(2025, 1, 6)  # Monday, January 6, 2025
        week_end = datetime(2025, 1, 12)   # Sunday, January 12, 2025
        
        # Format dates for the query (using the same format as the inventory API)
        start_date_str = '2025-01-06'
        end_date_str = '2025-01-12'
        
        # Get data for current week using the inventory API function
        # We'll use the same logic as the inventory API endpoint
        conn = get_db_connection()
        cursor = create_cursor(conn)
        
        try:
            # Get data from all brand tables for the week
            all_brands = ['aa_inventory', 'bob_inventory', 'cfo_inventory', 'gt_inventory', 'hrd_inventory', 'cz_inventory']
            weekly_data = []
            
            for table in all_brands:
                brand_code = table.split('_')[0].upper()
                if brand_code == 'BOB':
                    brand_code = 'BG'
                
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
                 AND ("Dates" = 'Monday, January 06, 2025' OR "Dates" = 'Tuesday, January 07, 2025' OR "Dates" = 'Wednesday, January 08, 2025' OR "Dates" = 'Thursday, January 09, 2025' OR "Dates" = 'Friday, January 10, 2025' OR "Dates" = 'Saturday, January 11, 2025' OR "Dates" = 'Sunday, January 12, 2025')
                ORDER BY inv."ID", 
                    CASE 
                        WHEN inv."Booked/Not Booked" = 'Booked' THEN 1
                        WHEN inv."Booked/Not Booked" = 'Hold' THEN 2
                        WHEN inv."Booked/Not Booked" = 'Hold ' THEN 2
                        WHEN inv."Booked/Not Booked" = 'hold' THEN 2
                        WHEN inv."Booked/Not Booked" = 'On hold' THEN 2
                        ELSE 3
                    END, inv."Dates" DESC
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        for row in results:
                weekly_data.append({
                    'slot_id': row[0],
                    'slot_date': row[1],
                    'status': row[2],
                    'booking_id': row[3],
                    'product': row[4],
                    'brand': row[5],
                    'client_name': row[6],
                    'contract_id': row[7]
                })
            
        finally:
        cursor.close()
        conn.close()
        
        # Process data by day
        days_data = {}
        for item in weekly_data:
            date = item['slot_date']
            if date not in days_data:
                days_data[date] = {'total': 0, 'booked': 0, 'available': 0, 'on_hold': 0}
            
            days_data[date]['total'] += 1
            if item['status'].lower() == 'booked':
                days_data[date]['booked'] += 1
            elif 'hold' in item['status'].lower():
                days_data[date]['on_hold'] += 1
            else:
                days_data[date]['available'] += 1
        
        # Convert to array format
        result = []
        for date, data in days_data.items():
            result.append({
                'date': date,
                'total': data['total'],
                'booked': data['booked'],
                'available': data['available'],
                'on_hold': data['on_hold'],
                'percentage': round((data['booked'] / data['total'] * 100) if data['total'] > 0 else 0, 2)
            })
        
        return jsonify(result)
    except Exception as e:
        print(f"Error in weekly overview API: {e}")
        return jsonify([]), 500

# HTML Template for the dashboard
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Campaign Inventory Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    
</head>
<body class="bg-gray-900 text-white">
    <div class="container mx-auto px-4 py-8">
        <!-- Header -->
        <header class="text-center mb-8">
            <h1 class="text-4xl font-bold text-blue-400 mb-2">📊 Campaign Inventory Dashboard</h1>
            <p class="text-gray-400">Real-time inventory tracking across all brands</p>
            <p class="text-sm text-gray-500 mt-2">Last updated: {{ datetime.now().strftime('%Y-%m-%d %H:%M:%S') }}</p>
        </header>


        <!-- Brand Overview Section -->
        <div class="bg-gray-800 rounded-lg p-6 border border-gray-700 mb-8">
            <h3 class="text-xl font-bold text-white mb-4 flex items-center">
                <svg class="w-6 h-6 mr-2 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                        </svg>
                Brand Overview
            </h3>
            <div id="brandOverview" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div class="text-center text-gray-400">Loading brand data...</div>
                </div>
            </div>

        <!-- Weekly Overview Section -->
        <div class="bg-gray-800 rounded-lg p-6 border border-gray-700 mb-8">
            <h3 class="text-xl font-bold text-white mb-4 flex items-center">
                <svg class="w-6 h-6 mr-2 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                        </svg>
                Weekly Overview
            </h3>
            <div id="weeklyOverview" class="grid grid-cols-1 md:grid-cols-7 gap-4">
                <div class="text-center text-gray-400">Loading weekly data...</div>
            </div>
        </div>

        <!-- Filters Section -->
        <div class="bg-gray-800 rounded-lg p-6 border border-gray-700 mb-8">
            <h2 class="text-xl font-bold text-white mb-4">🔍 Filters</h2>
            <div class="flex items-center space-x-4">
                <!-- Product Filter -->
                <div class="flex-1">
                    <label class="block text-sm font-medium text-gray-400 mb-2">Product</label>
                    <select id="productFilter" class="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
                        <option value="">All Products</option>
                        <option value="Newsletter_Sponsorship">Newsletter Sponsorship</option>
                        <option value="Original_Content_Production">Original Content Production</option>
                        <option value="Press_Release">Press Release</option>
                        <option value="Hosted_Content">Hosted Content</option>
                        <option value="Newsletter_Featured_Placement">Newsletter Featured Placement</option>
                        <option value="Newsletter_Category_Sponsorship">Newsletter Category Sponsorship</option>
                        <option value="Weekender_Newsletter_Sponsorship">Weekender Newsletter Sponsorship</option>
                        <option value="Mailshot">Mailshot</option>
                        <option value="Leading_Voice_Broadcast">Leading Voice Broadcast</option>
                        <option value="Original_Content_Newsletter_Feature_Placement">Original Content Newsletter Feature</option>
                        <option value="LinkedIn_Social_Media_Post">LinkedIn Social Media Post</option>
                        <option value="Press_Release_Promotion_Placement">Press Release Promotion</option>
                        <option value="NIAB_Event_Coverage">NIAB Event Coverage</option>
                        <option value="LinkedIn_Sponsor_Placement">LinkedIn Sponsor Placement</option>
                    </select>
                </div>
                
                <!-- Brand Filter -->
                <div class="flex-1">
                    <label class="block text-sm font-medium text-gray-400 mb-2">Brand</label>
                    <select id="brandFilter" class="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
                        <option value="">All Brands</option>
                        <option value="AA">Accountancy Age</option>
                        <option value="BG">Bobsguide</option>
                        <option value="CFO">The CFO</option>
                        <option value="GT">Global Treasurer</option>
                        <option value="HRD">HRD Connect</option>
                    </select>
                </div>
                
                <!-- Date Range Filter -->
                <div class="flex-1">
                    <label class="block text-sm font-medium text-gray-400 mb-2">Date Range</label>
                    <div class="flex space-x-2">
                        <input type="date" id="startDate" class="flex-1 bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
                        <input type="date" id="endDate" class="flex-1 bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
                    </div>
                </div>
                
                <!-- Client Filter -->
                <div class="flex-1">
                    <label class="block text-sm font-medium text-gray-400 mb-2">Client</label>
                    <div class="relative">
                        <input type="text" id="clientFilter" placeholder="Type to search clients..." class="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" autocomplete="off">
                        <div id="clientDropdown" class="absolute z-10 w-full bg-gray-700 border border-gray-600 rounded-lg mt-1 max-h-60 overflow-y-auto hidden">
                            <!-- Client options will be populated here -->
                        </div>
                    </div>
                </div>
                
                <!-- Status Filter -->
                <div class="flex-1">
                    <label class="block text-sm font-medium text-gray-400 mb-2">Status</label>
                    <select id="statusFilter" class="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
                        <option value="">All Status</option>
                        <option value="Booked">Booked</option>
                        <option value="Not Booked">Available</option>
                        <option value="Hold">On Hold</option>
                    </select>
                </div>
                
                <!-- Action Buttons -->
                <div class="flex items-end space-x-2">
                    <button onclick="applyFilters()" class="bg-blue-600 hover:bg-blue-700 text-white p-3 rounded-lg font-medium transition-colors">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                        </svg>
                    </button>
                    <button onclick="resetFilters()" class="bg-gray-600 hover:bg-gray-700 text-white p-3 rounded-lg font-medium transition-colors">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                        </svg>
                    </button>
                </div>
            </div>
        </div>

        <!-- Real-time Data Display -->
        <div class="bg-gray-800 rounded-lg p-6 border border-gray-700 mb-8">
            <h2 class="text-xl font-bold text-white mb-4">📊 Filtered Inventory Results</h2>
            <div class="overflow-x-auto">
                <table class="w-full text-sm">
                    <thead>
                        <tr class="border-b border-gray-700">
                            <th class="text-left py-2 text-gray-400">Product</th>
                            <th class="text-left py-2 text-gray-400">Brand</th>
                            <th class="text-left py-2 text-gray-400">Date</th>
                            <th class="text-left py-2 text-gray-400">Status</th>
                            <th class="text-left py-2 text-gray-400">Client Name</th>
                            <th class="text-left py-2 text-gray-400">Booking ID</th>
                        </tr>
                    </thead>
                    <tbody id="filteredResultsTable">
                        <tr class="border-b border-gray-700">
                            <td class="py-2 text-center text-gray-500" colspan="6">Apply filters to see inventory results</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Upcoming Deliverables -->
        <div class="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <h2 class="text-xl font-bold text-white mb-4">📅 Upcoming Deliverables (Next 2 Weeks)</h2>
            <div class="overflow-x-auto">
                <table class="w-full text-sm">
                    <thead>
                        <tr class="border-b border-gray-700">
                            <th class="text-left py-2 text-gray-400">Client</th>
                            <th class="text-left py-2 text-gray-400">Product</th>
                            <th class="text-left py-2 text-gray-400">Deliverable Date</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for deliverable in upcoming_deliverables %}
                        <tr class="border-b border-gray-700">
                            <td class="py-2 text-white">{{ deliverable.client }}</td>
                            <td class="py-2 text-blue-400">{{ deliverable.product }}</td>
                            <td class="py-2 text-gray-400">{{ deliverable.deliverable_date.strftime('%Y-%m-%d') if deliverable.deliverable_date else 'N/A' }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
                 // Chart.js removed - no longer needed

                 // Auto-refresh every 30 seconds - refresh the page to get latest data
         setInterval(() => {
             location.reload();
         }, 30000);

        // Filter functions
        function applyFilters() {
            const product = document.getElementById('productFilter').value;
            const brand = document.getElementById('brandFilter').value;
            const startDate = document.getElementById('startDate').value;
            const endDate = document.getElementById('endDate').value;
            const client = document.getElementById('clientFilter').value;
            const status = document.getElementById('statusFilter').value;
            
            // Build query parameters
            const params = new URLSearchParams();
            if (product) params.append('product', product);
            if (brand) params.append('brand', brand);
            if (startDate) params.append('start_date', startDate);
            if (endDate) params.append('end_date', endDate);
            if (client) params.append('client', client);
            if (status) params.append('status', status);
            
            // Show loading state
            const tbody = document.getElementById('filteredResultsTable');
            tbody.innerHTML = `
                <tr class="border-b border-gray-700">
                    <td class="py-2 text-center text-gray-500" colspan="6">Loading filtered results...</td>
                </tr>
            `;
            
                         // Fetch filtered data
             fetch(`/api/inventory?${params.toString()}`)
                 .then(response => response.json())
                 .then(data => {
                     updateFilteredResultsTable(data);
                 })
                .catch(error => {
                    console.log('Filter error:', error);
                    tbody.innerHTML = `
                        <tr class="border-b border-gray-700">
                            <td class="py-2 text-center text-red-500" colspan="6">Error loading data. Please try again.</td>
                        </tr>
                    `;
                });
        }
        
                 function resetFilters() {
             document.getElementById('productFilter').value = '';
             document.getElementById('brandFilter').value = '';
            document.getElementById('startDate').value = '2025-01-06';
            document.getElementById('endDate').value = '2025-01-20';
            document.getElementById('clientFilter').value = '';
            document.getElementById('statusFilter').value = '';
             // Clear the results table
             updateFilteredResultsTable([]);
         }
        
        // Load client data for filter
        let allClients = [];
        
        function loadClients() {
            fetch('/api/clients')
                .then(response => response.json())
                .then(data => {
                    allClients = data.map(client => client.client_name);
                    setupClientSearch();
                })
                .catch(error => console.log('Error loading clients:', error));
        }
        
        function setupClientSearch() {
            const clientInput = document.getElementById('clientFilter');
            const clientDropdown = document.getElementById('clientDropdown');
            
            clientInput.addEventListener('input', function() {
                const searchTerm = this.value.toLowerCase();
                const filteredClients = allClients.filter(client => 
                    client.toLowerCase().includes(searchTerm)
                );
                
                clientDropdown.innerHTML = '';
                
                if (searchTerm.length > 0 && filteredClients.length > 0) {
                    filteredClients.forEach(client => {
                        const option = document.createElement('div');
                        option.className = 'px-3 py-2 hover:bg-gray-600 cursor-pointer text-white';
                        option.textContent = client;
                        option.addEventListener('click', function() {
                            clientInput.value = client;
                            clientDropdown.classList.add('hidden');
                        });
                        clientDropdown.appendChild(option);
                    });
                    clientDropdown.classList.remove('hidden');
                } else {
                    clientDropdown.classList.add('hidden');
                }
            });
            
            // Hide dropdown when clicking outside
            document.addEventListener('click', function(e) {
                if (!clientInput.contains(e.target) && !clientDropdown.contains(e.target)) {
                    clientDropdown.classList.add('hidden');
                }
            });
        }

        // Load brand overview data
        function loadBrandOverview() {
            fetch('/api/brand-overview')
                .then(response => response.json())
                .then(data => {
                    const brandOverview = document.getElementById('brandOverview');
                    brandOverview.innerHTML = '';
                    
                    data.forEach(brand => {
                        const brandCard = document.createElement('div');
                        brandCard.className = 'bg-gray-700 rounded-lg p-4 border border-gray-600';
                        brandCard.innerHTML = `
                            <div class="text-center">
                                <h4 class="text-lg font-bold text-white mb-2">${brand.name}</h4>
                                <div class="grid grid-cols-2 gap-2 text-sm">
                                    <div>
                                        <p class="text-gray-400">Total</p>
                                        <p class="text-white font-bold">${brand.total_slots}</p>
                                    </div>
                                    <div>
                                        <p class="text-gray-400">Booked</p>
                                        <p class="text-green-400 font-bold">${brand.booked}</p>
                                    </div>
                                    <div>
                                        <p class="text-gray-400">Available</p>
                                        <p class="text-blue-400 font-bold">${brand.available}</p>
                                    </div>
                                    <div>
                                        <p class="text-gray-400">On Hold</p>
                                        <p class="text-yellow-400 font-bold">${brand.on_hold}</p>
                                    </div>
                                </div>
                                <div class="mt-3">
                                    <div class="w-full bg-gray-600 rounded-full h-2">
                                        <div class="bg-green-500 h-2 rounded-full" style="width: ${brand.percentage}%"></div>
                                    </div>
                                    <p class="text-xs text-gray-400 mt-1">${brand.percentage}% booked</p>
                                </div>
                            </div>
                        `;
                        brandOverview.appendChild(brandCard);
                    });
                })
                .catch(error => {
                    console.error('Error loading brand overview:', error);
                    document.getElementById('brandOverview').innerHTML = '<div class="text-center text-red-400">Error loading brand data</div>';
                });
        }

        // Load weekly overview data
        function loadWeeklyOverview() {
            fetch('/api/weekly-overview')
                .then(response => response.json())
                .then(data => {
                    const weeklyOverview = document.getElementById('weeklyOverview');
                    weeklyOverview.innerHTML = '';
                    
                    if (data.length === 0) {
                        weeklyOverview.innerHTML = '<div class="text-center text-gray-400 col-span-7">No data available for current week</div>';
                        return;
                    }
                    
                    data.forEach(day => {
                        const dayCard = document.createElement('div');
                        dayCard.className = 'bg-gray-700 rounded-lg p-3 border border-gray-600 text-center';
                        dayCard.innerHTML = `
                            <h4 class="text-sm font-bold text-white mb-2">${day.date.split(',')[0]}</h4>
                            <div class="space-y-1 text-xs">
                                <div class="flex justify-between">
                                    <span class="text-gray-400">Total:</span>
                                    <span class="text-white font-bold">${day.total}</span>
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-gray-400">Booked:</span>
                                    <span class="text-green-400 font-bold">${day.booked}</span>
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-gray-400">Available:</span>
                                    <span class="text-blue-400 font-bold">${day.available}</span>
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-gray-400">On Hold:</span>
                                    <span class="text-yellow-400 font-bold">${day.on_hold}</span>
                                </div>
                            </div>
                            <div class="mt-2">
                                <div class="w-full bg-gray-600 rounded-full h-1">
                                    <div class="bg-green-500 h-1 rounded-full" style="width: ${day.percentage}%"></div>
                                </div>
                                <p class="text-xs text-gray-400 mt-1">${day.percentage}%</p>
                            </div>
                        `;
                        weeklyOverview.appendChild(dayCard);
                    });
                })
                .catch(error => {
                    console.error('Error loading weekly overview:', error);
                    document.getElementById('weeklyOverview').innerHTML = '<div class="text-center text-red-400 col-span-7">Error loading weekly data</div>';
                });
         }
        
                          function updateFilteredResultsTable(data) {
            const tbody = document.getElementById('filteredResultsTable');
            tbody.innerHTML = '';
            
            if (!data || data.length === 0) {
                tbody.innerHTML = `
                    <tr class="border-b border-gray-700">
                        <td class="py-2 text-center text-gray-500" colspan="6">No results found for the selected filters</td>
                    </tr>
                `;
                return;
            }
            
            data.forEach(slot => {
                const row = document.createElement('tr');
                row.className = 'border-b border-gray-700';
                
                // Format date - handle both string dates and parsed dates
                let dateDisplay = 'N/A';
                if (slot.slot_date) {
                    try {
                        if (typeof slot.slot_date === 'string') {
                            dateDisplay = new Date(slot.slot_date).toLocaleDateString();
                        } else {
                            // If it's already a parsed date object
                            dateDisplay = slot.slot_date;
                        }
                    } catch (e) {
                        dateDisplay = 'Invalid Date';
                    }
                }
                
                // Color code status
                let statusClass = 'text-gray-400';
                if (slot.status === 'Booked') statusClass = 'text-green-400';
                else if (slot.status === 'On Hold') statusClass = 'text-yellow-400';
                
                row.innerHTML = `
                    <td class="py-2 text-blue-400">${slot.product}</td>
                    <td class="py-2 text-white">${slot.brand}</td>
                    <td class="py-2 text-gray-400">${dateDisplay}</td>
                    <td class="py-2 ${statusClass}">${slot.status}</td>
                    <td class="py-2 text-white">${slot.client_name}</td>
                    <td class="py-2 text-gray-400">${slot.booking_id || 'N/A'}</td>
                `;
                tbody.appendChild(row);
            });
        }
        
        // Set default date range to January 2025 (where we have data)
        window.addEventListener('load', function() {
            // Set to January 6-20, 2025 where we have actual data
            document.getElementById('startDate').value = '2025-01-06';
            document.getElementById('endDate').value = '2025-01-20';
            
            // Load clients for filter
            loadClients();
            
            // Load brand overview
            loadBrandOverview();
            
            // Load weekly overview
            loadWeeklyOverview();
            
            // Load data immediately with the default range
            applyFilters();
        });
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    # Force redeploy - updated to ensure latest endpoints are available - v4
    port = int(os.getenv('PORT', 5005))
    app.run(debug=True, port=port)
