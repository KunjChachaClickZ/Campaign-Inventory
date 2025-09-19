# 📊 Campaign Inventory Dashboard

A modern web-based dashboard for real-time campaign inventory management across multiple media brands, built with Flask, PostgreSQL, and Tailwind CSS.

## 🚀 Features

- **📈 Real-time Inventory Tracking**: Monitor available, booked, and on-hold inventory slots across 6 brands
- **🏢 Multi-Brand Support**: Accountancy Age (AA), Bobsguide (BG), The CFO (CFO), Global Treasurer (GT), HRD Connect (HRD), ClickZ (CZ)
- **🔍 Advanced Filtering**: Filter by brand, product, date range, client, and status
- **📊 Interactive Dashboard**: View key metrics, brand performance, and inventory summaries
- **🔗 API-First Architecture**: RESTful Flask API with CORS support
- **📱 Responsive Design**: Modern UI with Tailwind CSS for all devices
- **⚡ Connection Pooling**: Efficient PostgreSQL connection management with psycopg-binary
- **📅 Smart Date Handling**: Automatic date conversion and range filtering

## 📋 Prerequisites

- **Python 3.9+**
- **PostgreSQL database** (AWS RDS)
- **Web browser** (Chrome, Firefox, Safari, Edge)
- **GitHub Pages** (for frontend hosting)
- **Render.com account** (for backend hosting)

## 🛠️ Installation

### Local Development

1. **Clone the repository**:
   ```bash
   git clone https://github.com/KunjChachaClickZ/Campaign-Inventory.git
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

5. **Run the application**:
   ```bash
   python simple_dashboard.py
   ```

   Access at: http://localhost:5005

## 🎯 Usage

### 🌐 Live Dashboard

**Access the dashboard at: https://campaign-inventory-api.onrender.com**

### 📊 Dashboard Sections

#### **Weekly Overview (Top Section)**
- **Real-time date display**: Shows current Monday-Sunday range
- **Brand performance cards**: Booked vs Filled counts per brand
- **Week navigation**: "Next Week" and "Week After" buttons
- **Professional layout**: Clean, corporate-ready design

#### **Brand Performance Overview**
- **6 brand cards** in responsive grid layout
- **Utilization metrics**: Booked/Available ratios with percentages
- **Color-coded indicators**: Green/Yellow/Red based on utilization
- **Interactive elements**: Hover effects and click-to-expand modals

#### **Advanced Filtering System**
- **🔍 Client Search**: Type-ahead autocomplete (100+ clients)
- **📦 Product Filter**: Newsletter sponsorships, mailshots, content production
- **🏢 Brand Filter**: All 6 brands with dropdown selection
- **📅 Date Range**: Flexible start/end date pickers
- **📊 Status Filter**: Booked, Available, On Hold options

#### **Results Table**
- **Paginated display**: 20 results per page
- **Real-time updates**: Instant filtering and search
- **Export ready**: Framework for CSV/JSON export (planned)
- **Responsive design**: Works on all screen sizes

## 🏗️ Architecture

### Core Components

1. **Flask Backend** (`simple_dashboard.py`):
   - RESTful API endpoints
   - PostgreSQL database integration with psycopg-binary
   - Connection pooling for performance
   - CORS support for frontend communication
   - Environment variable configuration

2. **Web Frontend** (`index.html`):
   - Modern dashboard UI with Tailwind CSS
   - JavaScript-powered interactivity
   - Real-time API communication
   - Responsive design for all devices
   - Advanced filtering and search

3. **Database Layer**:
   - PostgreSQL with AWS RDS hosting
   - Multiple brand-specific inventory tables
   - Campaign ledger for booking data
   - Optimized queries with proper indexing

### Database Schema

The system works with these key database tables:
- **Inventory Tables**: `{brand}_inventory` (6 tables: aa_inventory, bob_inventory, etc.)
- **Campaign Ledger**: `campaign_ledger` (booking details and client information)
- **Form Submissions**: `sponsorship_bookings_form_submissions` (lead tracking)

## 🔧 Configuration

### Environment Variables
```env
DB_HOST=contentive-warehouse-instance-1.cq8sion7djdk.eu-west-2.rds.amazonaws.com
DB_PORT=5432
DB_NAME=analytics
DB_USER=kunj.chacha@contentive.com
DB_PASSWORD=your-password-here
DATABASE_URL=postgresql://user:pass@host:port/dbname  # Alternative format
```

### Database Connection
The system uses **psycopg-binary** for reliable PostgreSQL connectivity with:
- Connection pooling for optimal performance
- Automatic reconnection on failures
- Environment-based configuration

## 📈 Performance Features

- **Connection Pooling**: Reuses database connections efficiently
- **API Caching**: 30-second cache for frequently accessed data
- **Lazy Loading**: Data loaded only when needed
- **Optimized Queries**: Efficient SQL with proper JOINs and WHERE clauses
- **Real-time Updates**: Auto-refresh every 30 seconds

## 🚀 Deployment

### Backend (Render.com)
The Flask API is deployed on Render.com with:
- **Service Name**: `campaign-inventory-api`
- **Runtime**: Python 3.11.7
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn simple_dashboard:app --bind 0.0.0.0:$PORT`
- **Live URL**: https://campaign-inventory-api.onrender.com

### Frontend (GitHub Pages)
The dashboard can be deployed to GitHub Pages:
1. Go to repository Settings → Pages
2. Select "Deploy from a branch"
3. Choose `main` branch and `/ (root)` folder
4. Access at: `https://kunjchachaclickz.github.io/Campaign-Inventory/`

## 🔗 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main dashboard page |
| `/api/brand-overview` | GET | Brand performance summary |
| `/api/inventory` | GET | Filtered inventory results |
| `/api/clients` | GET | Client list for autocomplete |
| `/api/weekly-comparison` | GET | Weekly booked vs filled data |
| `/api/brand-product-breakdown` | GET | Product performance by brand |

## 📊 Business Value

### For Sales Teams
- **Real-time visibility** into inventory availability
- **Quick identification** of high-performing products
- **Client booking history** and trends analysis
- **Data-driven campaign planning**

### For Clients
- **Transparent view** of available inventory slots
- **Flexible filtering** by preferred products/brands
- **Weekly performance tracking** for booked campaigns
- **Self-service booking insights**

### For Management
- **Brand-wise performance analytics**
- **Booking rate optimization insights**
- **Revenue forecasting** based on inventory utilization
- **Cross-brand inventory management**

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
1. Check the deployment logs in Render.com dashboard
2. Review browser console for frontend errors
3. Check database connectivity and credentials
4. Contact the development team

## 🔮 Future Enhancements

- [ ] CSV/JSON data export functionality
- [ ] Advanced analytics and reporting
- [ ] Real-time notifications for inventory changes
- [ ] Multi-user authentication and permissions
- [ ] Integration with external booking systems
- [ ] Automated inventory optimization suggestions
- [ ] Mobile app companion
- [ ] API rate limiting and monitoring
- [ ] Automated testing and CI/CD pipeline

---

**Built with ❤️ for efficient campaign inventory management**

**Live Dashboard**: https://campaign-inventory-api.onrender.com

**Repository**: https://github.com/KunjChachaClickZ/Campaign-Inventory</content>
</xai:function_call"> 

<xai:function_call>  
<xai:function_call name="run_terminal_cmd">
<parameter name="command">source venv/bin/activate && python simple_dashboard.py