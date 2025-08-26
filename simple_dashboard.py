from flask import Flask, render_template_string, jsonify, request
from datetime import datetime, timedelta
from flask_cors import CORS
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import pg8000 for PostgreSQL connection
try:
    import pg8000
    PG8000_AVAILABLE = True
    print("Using pg8000 for PostgreSQL connection")
except ImportError as e:
    print(f"Error: pg8000 not available: {e}")
    PG8000_AVAILABLE = False

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Database configuration - use environment variables for deployment
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'contentive-warehouse-instance-1.cq8sion7djdk.eu-west-2.rds.amazonaws.com'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'analytics'),
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
        'database': url.path[1:],
        'user': url.username,
        'password': url.password
    }

def get_db_connection():
    try:
        if PG8000_AVAILABLE:
            conn = pg8000.connect(**DB_CONFIG)
            print("Database connection successful with pg8000!")
            return conn
        else:
            raise Exception("pg8000 not available")
    except Exception as e:
        print(f"Database connection error: {e}")
        raise e

def create_cursor(conn):
    """Create a cursor"""
    return conn.cursor()

def get_inventory_summary(product_filter=None, brand_filter=None, start_date=None, end_date=None):
    """Get summary of all inventory data with optional filters"""
    conn = get_db_connection()
    cursor = create_cursor(conn)
    
    try:
        # Build base query with filters
        base_where = 'WHERE "ID" >= 8000'
        
        # Add date filter if specified (using the actual "Dates" column)
        if start_date and end_date:
            base_where += f' AND "Dates" >= \'{start_date}\' AND "Dates" <= \'{end_date}\''
        
        # Get summary from all inventory tables - using DISTINCT for accurate counting
        query = f"""
        SELECT 
            'Accountancy Age' as brand,
            COUNT(DISTINCT "ID") as total_slots,
            COUNT(DISTINCT CASE WHEN "Booked/Not Booked" = 'Booked' THEN "ID" END) as booked,
            COUNT(DISTINCT CASE WHEN "Booked/Not Booked" = 'Not Booked' THEN "ID" END) as available,
            COUNT(DISTINCT CASE WHEN "Booked/Not Booked" = 'Hold' THEN "ID" END) as on_hold,
            COUNT(DISTINCT CASE WHEN "Booked/Not Booked" IS NULL OR "Booked/Not Booked" NOT IN ('Booked', 'Not Booked', 'Hold') THEN "ID" END) as unclassified
        FROM campaign_metadata.aa_inventory
        {base_where}
        """
        
        # Execute queries for each brand
        brands_data = []
        brand_tables = [
            ('Accountancy Age', 'aa_inventory'),
            ('Bobsguide', 'bob_inventory'),
            ('The CFO', 'cfo_inventory'),
            ('Global Treasurer', 'gt_inventory'),
            ('HRD Connect', 'hrd_inventory')
        ]
        
        for brand_name, table_name in brand_tables:
            # Skip if brand filter is specified and doesn't match
            if brand_filter and brand_filter != brand_name:
                continue
                
            try:
                brand_query = query.replace('aa_inventory', table_name)
                cursor.execute(brand_query)
                brand_data = cursor.fetchone()
                
                if brand_data:
                    # For pg8000, data comes as tuple: (brand, total_slots, booked, available, on_hold, unclassified)
                    available_with_unclassified = brand_data[3] + brand_data[5]
                    brands_data.append({
                        'brand': brand_name,
                        'total_slots': brand_data[1],
                        'booked': brand_data[2],
                        'available': available_with_unclassified,
                        'on_hold': brand_data[4],
                        'unclassified': brand_data[5]
                    })
            except Exception as e:
                print(f"Error querying {table_name}: {e}")
                # Add empty data for this brand if query fails
                brands_data.append({
                    'brand': brand_name,
                    'total_slots': 0,
                    'booked': 0,
                    'available': 0,
                    'on_hold': 0,
                    'unclassified': 0
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
                    'unclassified': brand_data['unclassified']
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

def get_filtered_inventory_slots(product_filter=None, brand_filter=None, start_date=None, end_date=None):
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
            ('hrd_inventory', 'HRD')
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
                    'HRD Connect': 'HRD'
                }
                expected_brand_code = brand_mapping.get(brand_filter, brand_filter)
                if brand_code != expected_brand_code:
                    continue
                
            # Build query for this brand table - using DISTINCT to eliminate duplicates
            query = f"""
            SELECT DISTINCT ON ("ID")
                "ID" as slot_id,
                "Dates" as slot_date,
                "Booked/Not Booked" as status,
                "Booking ID" as booking_id,
                "Media_Asset" as product,
                '{brand_code}' as brand
            FROM campaign_metadata.{table_name}
            WHERE "ID" >= 8000
            """
            
            # Add date filter if specified - now properly implemented
            if start_date and end_date:
                print(f"Filtering by date range: {start_date} to {end_date}")
                
                # Convert date format from YYYY-MM-DD to the format used in database
                try:
                    from datetime import datetime
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                    
                    # Generate all weekdays between start and end date
                    from datetime import timedelta
                    current_dt = start_dt
                    date_conditions = []
                    
                    while current_dt <= end_dt:
                        # Skip weekends (Saturday=5, Sunday=6)
                        if current_dt.weekday() < 5:  # Monday=0 to Friday=4
                            # Format as "Monday, August 25, 2025"
                            formatted_date = current_dt.strftime('%A, %B %d, %Y')
                            date_conditions.append(f'"Dates" = \'{formatted_date}\'')
                        current_dt += timedelta(days=1)
                    
                    if date_conditions:
                        query += f" AND ({' OR '.join(date_conditions)})"
                        print(f"Added date conditions: {date_conditions}")
                    
                except Exception as e:
                    print(f"Error parsing dates: {e}")
                    # Fallback to original hardcoded conditions for known ranges
                    if start_date == '2025-08-25' and end_date == '2025-08-29':
                        date_conditions = [
                            '"Dates" = \'Monday, August 25, 2025\'',
                            '"Dates" = \'Tuesday, August 26, 2025\'',
                            '"Dates" = \'Wednesday, August 27, 2025\'',
                            '"Dates" = \'Thursday, August 28, 2025\'',
                            '"Dates" = \'Friday, August 29, 2025\''
                        ]
                        query += f" AND ({' OR '.join(date_conditions)})"
                    elif start_date == '2025-08-18' and end_date == '2025-08-22':
                        date_conditions = [
                            '"Dates" = \'Monday, August 18, 2025\'',
                            '"Dates" = \'Tuesday, August 19, 2025\'',
                            '"Dates" = \'Wednesday, August 20, 2025\'',
                            '"Dates" = \'Thursday, August 21, 2025\'',
                            '"Dates" = \'Friday, August 22, 2025\''
                        ]
                        query += f" AND ({' OR '.join(date_conditions)})"
            
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
                query += f" AND \"Media_Asset\" = '{db_product_name}'"
            
            # Add ORDER BY clause for DISTINCT ON
            query += " ORDER BY \"ID\", \"Dates\" DESC"
            
            print(f"Executing query for {table_name}: {query}")
            cursor.execute(query)
            brand_results = cursor.fetchall()
            print(f"Found {len(brand_results)} results for {table_name}")
            
            # Process results for this brand
            for row in brand_results:
                try:
                    # pg8000 returns tuples: (slot_id, slot_date, status, booking_id, product, brand)
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
                        'slot_date': str(row[1]) if row[1] is not None else '',   # slot_date
                        'status': row[2] if row[2] is not None else '',           # status
                        'booking_id': row[3] if row[3] is not None else '',       # booking_id
                        'product': row[4] if row[4] is not None else 'Mailshot'   # product
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
            # pg8000 returns tuples: (client, product, deliverable_date)
            deliverables.append({
                'client': row[0],           # client
                'product': row[1],          # product
                'deliverable_date': row[2]  # deliverable_date
            })
        
        return deliverables
        
    finally:
        cursor.close()
        conn.close()

@app.route('/')
def dashboard():
    """Main dashboard page"""
    try:
        # Use the new function that breaks down by product and brand by default
        inventory_summary = get_inventory_by_product_and_brand()
        upcoming_deliverables = get_upcoming_deliverables()
        
        # Calculate totals
        total_slots = sum(item['total_slots'] for item in inventory_summary)
        total_booked = sum(item['booked'] for item in inventory_summary)
        total_available = sum(item['available'] for item in inventory_summary)
        total_on_hold = sum(item['on_hold'] for item in inventory_summary)
        
        return render_template_string(HTML_TEMPLATE, 
                                    inventory_summary=inventory_summary,
                                    upcoming_deliverables=upcoming_deliverables,
                                    total_slots=total_slots,
                                    total_booked=total_booked,
                                    total_available=total_available,
                                    total_on_hold=total_on_hold,
                                    datetime=datetime)
    except Exception as e:
        return f"Error: {str(e)}", 500

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
        
        # Always use the filtered inventory slots function for detailed results
        inventory_slots = get_filtered_inventory_slots(
            product_filter=product_filter,
            brand_filter=brand_filter,
            start_date=start_date,
            end_date=end_date
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
            "Campaign Name" as campaign_name,
            "Client Name" as client,
            "Product Name - As per Listing Hub" as product,
            "Brand" as brand,
            "Scheduled Live Date" as start_date,
            "End Date" as end_date,
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
            # pg8000 returns tuples: (id, campaign_name, client, product, brand, start_date, end_date, status)
            result.append({
                'id': row[0],                                    # id
                'campaign_name': row[1],                         # campaign_name
                'client': row[2],                                # client
                'product': row[3],                               # product
                'brand': row[4],                                 # brand
                'start_date': str(row[5]) if row[5] else None,   # start_date
                'end_date': str(row[6]) if row[6] else None,     # end_date
                'status': row[7]                                 # status
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
        
        # Format the data for the frontend
        result = {}
        for brand_data in brands_data:
            brand_name = brand_data['brand']
            result[brand_name] = {
                'total_slots': brand_data['total_slots'],
                'booked': brand_data['booked'],
                'on_hold': brand_data['on_hold'],
                'not_booked': brand_data['available'],  # This maps to 'available' in our data
                'tableSources': [
                    {
                        'label': brand_name,
                        'value': brand_name.lower().replace(' ', '_'),
                        'count': brand_data['total_slots']
                    }
                ]
            }
        
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

        <!-- Summary Cards -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div class="bg-gray-800 rounded-lg p-6 border border-gray-700">
                <div class="flex items-center">
                    <div class="p-3 rounded-full bg-blue-500 bg-opacity-20">
                        <svg class="w-6 h-6 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                        </svg>
                    </div>
                    <div class="ml-4">
                        <p class="text-gray-400 text-sm">Total Slots</p>
                        <p class="text-2xl font-bold text-white">{{ total_slots }}</p>
                    </div>
                </div>
            </div>

            <div class="bg-gray-800 rounded-lg p-6 border border-gray-700">
                <div class="flex items-center">
                    <div class="p-3 rounded-full bg-green-500 bg-opacity-20">
                        <svg class="w-6 h-6 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                        </svg>
                    </div>
                    <div class="ml-4">
                        <p class="text-gray-400 text-sm">Booked</p>
                        <p class="text-2xl font-bold text-green-400">{{ total_booked }}</p>
                    </div>
                </div>
            </div>

            <div class="bg-gray-800 rounded-lg p-6 border border-gray-700">
                <div class="flex items-center">
                    <div class="p-3 rounded-full bg-yellow-500 bg-opacity-20">
                        <svg class="w-6 h-6 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                        </svg>
                    </div>
                    <div class="ml-4">
                        <p class="text-gray-400 text-sm">On Hold</p>
                        <p class="text-2xl font-bold text-yellow-400">{{ total_on_hold }}</p>
                    </div>
                </div>
            </div>

            <div class="bg-gray-800 rounded-lg p-6 border border-gray-700">
                <div class="flex items-center">
                    <div class="p-3 rounded-full bg-gray-500 bg-opacity-20">
                        <svg class="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"></path>
                        </svg>
                    </div>
                    <div class="ml-4">
                        <p class="text-gray-400 text-sm">Available</p>
                        <p class="text-2xl font-bold text-gray-400">{{ total_available }}</p>
                    </div>
                </div>
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
                        <option value="BM-S2-Newsletter Sponsorship">Newsletter Sponsorship</option>
                        <option value="MailShot">Mailshot</option>
                        <option value="LB-1-Live Broadcast">Live Broadcast</option>
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
                
                <!-- Search Button -->
                <div class="flex items-end">
                    <button onclick="applyFilters()" class="bg-blue-600 hover:bg-blue-700 text-white p-3 rounded-lg font-medium transition-colors">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
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
            
            // Build query parameters
            const params = new URLSearchParams();
            if (product) params.append('product', product);
            if (brand) params.append('brand', brand);
            if (startDate) params.append('start_date', startDate);
            if (endDate) params.append('end_date', endDate);
            
                         // Fetch filtered data
             fetch(`/api/inventory?${params.toString()}`)
                 .then(response => response.json())
                 .then(data => {
                     updateFilteredResultsTable(data);
                 })
                 .catch(error => console.log('Filter error:', error));
        }
        
                 function resetFilters() {
             document.getElementById('productFilter').value = '';
             document.getElementById('brandFilter').value = '';
             document.getElementById('startDate').value = '';
             document.getElementById('endDate').value = '';
             // Clear the results table
             updateFilteredResultsTable([]);
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
        
        // Set default date range to next 2 weeks
        window.addEventListener('load', function() {
            const today = new Date();
            const twoWeeksLater = new Date(today.getTime() + (14 * 24 * 60 * 60 * 1000));
            
            document.getElementById('startDate').value = today.toISOString().split('T')[0];
            document.getElementById('endDate').value = twoWeeksLater.toISOString().split('T')[0];
        });
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(debug=True, port=5000)
