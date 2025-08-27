# 📊 Campaign Inventory Dashboard

A real-time inventory tracking dashboard for campaign management across multiple brands.

## 🚀 Features

### ✅ **Enhanced Dashboard Features:**
- **📈 Brand Overview**: Static overview showing booking percentages for all brands
- **🔍 Advanced Filtering**: Filter by Product, Brand, Date Range, and Status
- **📊 Real-time Data**: Live data from PostgreSQL database
- **🎯 Two-Stage Filtering**: Initial filters + additional status filtering
- **📱 Responsive Design**: Works on desktop and mobile devices

### 📋 **Available Products:**
- Hosted Content
- LVB Mailshot
- Leading Voice Broadcast
- Mailshot
- Newsletter Category Sponsorship
- Newsletter Featured Placement
- Newsletter Sponsorship
- Original Content Production
- Weekender Newsletter Sponsorship

### 🏢 **Supported Brands:**
- Accountancy Age (AA)
- Bobsguide (BG)
- The CFO (CFO)
- Global Treasurer (GT)
- HRD Connect (HRD)

## 🛠️ Setup Instructions

### **Backend Setup (Flask API):**

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Database Configuration:**
   - Ensure PostgreSQL database is running
   - Update database connection in `simple_dashboard.py`

3. **Start Flask Server:**
   ```bash
   python simple_dashboard.py
   ```
   - Server runs on: `http://localhost:5000`

### **Frontend Setup:**

1. **Local Development:**
   - Open `index.html` in your browser
   - Or use a local server: `python -m http.server 8000`

2. **GitHub Pages Deployment:**
   - Push to GitHub repository
   - Enable GitHub Pages in repository settings
   - Access at: `https://kunjchachaclickz.github.io/Campaign-Inventory/`

## 📡 API Endpoints

### **Main Inventory Endpoint:**
```
GET /api/inventory
```

**Query Parameters:**
- `product`: Filter by product type
- `brand`: Filter by brand (AA, BG, CFO, GT, HRD)
- `start_date`: Start date (YYYY-MM-DD)
- `end_date`: End date (YYYY-MM-DD)
- `status`: Filter by status (Booked, Available, On Hold)

**Example:**
```
GET /api/inventory?product=Mailshot&brand=AA&start_date=2025-08-25&end_date=2025-08-29&status=Booked
```

### **Other Endpoints:**
- `GET /api/campaign-ledger`: Campaign ledger data
- `GET /api/brand-overview`: Brand overview statistics
- `GET /api/current-week-inventory`: Current week inventory

## 🎯 Usage Guide

### **1. View Brand Overview:**
- The top section shows booking percentages for all brands
- Color-coded: Green (≥70%), Yellow (40-69%), Red (<40%)
- Updates on page refresh

### **2. Apply Filters:**
- **Product**: Select specific product type
- **Brand**: Choose specific brand
- **Date Range**: Set start and end dates
- **Search**: Click "Search" to apply filters

### **3. Further Filter Results:**
- After getting initial results, use the "Further Filter Results" section
- **Status Filter**: Filter by Booked, Available, or On Hold
- **Apply**: Click "Filter by Status" to refine results

### **4. Reset Filters:**
- Click "Reset" to clear all filters
- Click "Clear Status Filter" to clear only status filter

## 🔧 Technical Details

### **Frontend:**
- **HTML5** with **Tailwind CSS**
- **Vanilla JavaScript** (no framework dependencies)
- **Responsive design** for all screen sizes

### **Backend:**
- **Python Flask** API
- **PostgreSQL** database with psycopg2
- **CORS enabled** for cross-origin requests

### **Database Schema:**
- Tables: `aa_inventory`, `bob_inventory`, `cfo_inventory`, `gt_inventory`, `hrd_inventory`
- Schema: `campaign_metadata`
- Key columns: `ID`, `Dates`, `Booked/Not Booked`, `Booking ID`, `Media_Asset`

## 🚀 Deployment

### **GitHub Pages:**
1. Push code to GitHub repository
2. Go to Settings → Pages
3. Select source: "Deploy from a branch"
4. Choose branch: `main`
5. Access URL: `https://kunjchachaclickz.github.io/Campaign-Inventory/`

### **Backend Deployment (Optional):**
- Deploy Flask app to Render.com, Heroku, or similar
- Update `API_BASE` URL in `index.html`
- Ensure CORS allows GitHub Pages domain

## 📊 Data Flow

1. **Page Load**: Fetches overview data and initial inventory data
2. **Filter Application**: Sends filter parameters to API
3. **Status Filtering**: Client-side filtering of results
4. **Real-time Updates**: Data refreshes on filter changes

## 🔍 Troubleshooting

### **Common Issues:**

1. **"Error loading data"**
   - Check if Flask server is running
   - Verify database connection
   - Check browser console for errors

2. **"CORS Error"**
   - Ensure Flask-CORS is installed
   - Check CORS configuration in `simple_dashboard.py`

3. **"No results found"**
   - Verify date format (YYYY-MM-DD)
   - Check product/brand names match exactly
   - Ensure database has data for selected filters

### **Debug Mode:**
- Open browser developer tools (F12)
- Check Console tab for API calls and errors
- Check Network tab for request/response details

## 📝 Recent Updates

### **v2.0 - Enhanced Dashboard:**
- ✅ Added Brand Overview section
- ✅ Expanded product dropdown (9 products)
- ✅ Added status filtering below results
- ✅ Improved UI/UX design
- ✅ GitHub Pages deployment ready

### **v1.0 - Basic Dashboard:**
- ✅ Basic filtering functionality
- ✅ Real-time data display
- ✅ Date range filtering
- ✅ Product and brand filtering

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review browser console for errors
3. Verify API endpoints are working
4. Check database connectivity

---

**Last Updated**: August 25, 2025
**Version**: 2.0
**Status**: Production Ready ✅
