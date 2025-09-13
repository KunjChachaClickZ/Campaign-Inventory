# Campaign Inventory Management System

A powerful command-line tool for managing campaign inventory across multiple brands, built with Python and PostgreSQL.

## 🚀 Features

- **Real-time Inventory Tracking**: Monitor available, booked, and on-hold inventory slots across 6 brands
- **Multi-Brand Support**: Accountancy Age (AA), Bobsguide (BG), The CFO (CFO), Global Treasurer (GT), HRD Connect (HRD), ClickZ (CZ)
- **Advanced Filtering**: Filter by brand, product, date range, client, and status
- **Data Export**: Export data to CSV or JSON formats
- **Interactive Dashboard**: View key metrics and inventory summaries
- **Connection Pooling**: Efficient database connection management
- **Date Range Support**: Flexible date filtering with proper database format handling

## 📋 Prerequisites

- Python 3.9+
- PostgreSQL database access
- Required Python packages (see requirements.txt)

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd Campaign-Inventory
   ```

2. **Create virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   Create a `.env` file with your database credentials:
   ```env
   DB_HOST=your-database-host
   DB_PORT=5432
   DB_NAME=analytics
   DB_USER=your-username
   DB_PASSWORD=your-password
   ```

## 🎯 Usage

### Basic Commands

#### Show Dashboard
```bash
python3 cli.py dashboard
```
Displays a comprehensive dashboard with:
- Brand overview with utilization rates
- Recent inventory slots
- Key metrics and statistics

#### List Inventory
```bash
# List all inventory slots
python3 cli.py list

# Filter by date range
python3 cli.py list --start-date 2025-01-06 --end-date 2025-01-10

# Filter by brand
python3 cli.py list --brand "Accountancy Age"

# Filter by product
python3 cli.py list --product "Press_Release"

# Filter by status
python3 cli.py list --status "booked"

# Combine filters
python3 cli.py list --brand "AA" --start-date 2025-01-06 --end-date 2025-01-10
```

#### Show Available Options
```bash
# Show available brands
python3 cli.py brands

# Show available products
python3 cli.py products
```

#### Export Data
```bash
# Export inventory to CSV
python3 cli.py export inventory --format csv --start-date 2025-01-06 --end-date 2025-01-10

# Export brand summaries to JSON
python3 cli.py export brands --format json

# Export with filters
python3 cli.py export inventory --format csv --brand "AA" --product "Press_Release"
```

### Advanced Usage

#### Custom Date Ranges
The system supports flexible date filtering. Dates are automatically converted to the database format:
```bash
python3 cli.py list --start-date 2025-01-06 --end-date 2025-01-20
```

#### Filtering Options
- **Brand**: Filter by specific brand (AA, BG, CFO, GT, HRD, CZ)
- **Product**: Filter by product type (Press_Release, Mailshot, etc.)
- **Status**: Filter by booking status (booked, available, hold)
- **Client**: Filter by client name
- **Date Range**: Filter by date range

## 🏗️ Architecture

### Core Components

1. **Database Module** (`database.py`):
   - Connection pooling for efficient database access
   - Query execution with automatic connection management
   - Support for complex date filtering

2. **Data Models** (`models.py`):
   - `InventorySlot`: Represents individual inventory slots
   - `BrandSummary`: Brand-level inventory summaries
   - `Client`: Client information and metrics
   - `CampaignMetrics`: Overall campaign KPIs
   - `FilterOptions`: Flexible filtering system

3. **CLI Interface** (`cli.py`):
   - Command-line interface with argparse
   - Interactive dashboard display
   - Data export functionality
   - Comprehensive error handling

### Database Schema

The system works with the following key tables:
- **Inventory Tables**: `{brand}_inventory` (6 tables)
- **Campaign Ledger**: `campaign_ledger`
- **Booking Tables**: `{brand}_{product}_booking`

## 📊 Data Models

### InventorySlot
```python
@dataclass
class InventorySlot:
    slot_id: int
    slot_date: str
    status: str
    booking_id: str
    product: str
    brand: str
    client_name: str
    contract_id: str
```

### BrandSummary
```python
@dataclass
class BrandSummary:
    brand: str
    name: str
    total_slots: int
    booked: int
    available: int
    on_hold: int
    percentage: float
```

## 🔧 Configuration

### Environment Variables
- `DB_HOST`: Database host
- `DB_PORT`: Database port (default: 5432)
- `DB_NAME`: Database name
- `DB_USER`: Database username
- `DB_PASSWORD`: Database password
- `DATABASE_URL`: Alternative database URL format

### Database Connection
The system uses pg8000 for PostgreSQL connectivity with connection pooling for optimal performance.

## 📈 Performance Features

- **Connection Pooling**: Reuses database connections for better performance
- **Efficient Queries**: Optimized SQL queries with proper indexing
- **Lazy Loading**: Data is loaded only when needed
- **Memory Management**: Automatic cleanup of database connections

## 🚨 Error Handling

The system includes comprehensive error handling:
- Database connection errors
- Query execution errors
- Invalid date formats
- Missing required parameters
- Graceful degradation on errors

## 📝 Examples

### Daily Inventory Check
```bash
# Check today's inventory
python3 cli.py dashboard

# Export today's data
python3 cli.py export inventory --format csv --start-date $(date +%Y-%m-%d) --end-date $(date +%Y-%m-%d)
```

### Weekly Report
```bash
# Generate weekly report
python3 cli.py list --start-date 2025-01-06 --end-date 2025-01-12

# Export weekly data
python3 cli.py export inventory --format csv --start-date 2025-01-06 --end-date 2025-01-12
```

### Brand-Specific Analysis
```bash
# Analyze specific brand
python3 cli.py list --brand "Accountancy Age" --start-date 2025-01-01 --end-date 2025-01-31

# Export brand data
python3 cli.py export inventory --format json --brand "AA"
```

## 🔄 Migration from Flask

This CLI system replaces the previous Flask web application with:
- ✅ Better performance (no web server overhead)
- ✅ Easier automation and scripting
- ✅ Command-line integration
- ✅ Data export capabilities
- ✅ Simplified deployment

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For support and questions:
1. Check the documentation
2. Review the examples
3. Check the issue tracker
4. Contact the development team

## 🔮 Future Enhancements

- [ ] Real-time monitoring
- [ ] Advanced analytics
- [ ] Automated reporting
- [ ] Web interface option
- [ ] API endpoints
- [ ] Integration with external systems

---

**Built with ❤️ for efficient campaign inventory management**