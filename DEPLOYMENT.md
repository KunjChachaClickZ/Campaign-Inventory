# 🚀 Deployment Guide - Campaign Inventory Dashboard

## 📋 Prerequisites
- GitHub repository with your code
- Render.com account (free tier available)
- PostgreSQL database (AWS RDS in your case)

## 🔧 Backend Deployment (Render.com)

### Step 1: Connect GitHub to Render
1. Go to [Render.com](https://render.com) and sign up/login
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub account
4. Select your repository: `Kunjchacha/Campaign-Inventory`

### Step 2: Configure Web Service
- **Name**: `campaign-inventory-api`
- **Environment**: `Python 3.11`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn simple_dashboard:app --bind 0.0.0.0:$PORT`

### Step 3: Set Environment Variables
Add these environment variables in Render dashboard:

```
DB_HOST=contentive-warehouse-instance-1.cq8sion7djdk.eu-west-2.rds.amazonaws.com
DB_PORT=5432
DB_NAME=analytics
DB_USER=kunj.chacha@contentive.com
DB_PASSWORD=(iRFw989b{5h
```

### Step 4: Deploy
1. Click **"Create Web Service"**
2. Wait for build to complete (2-3 minutes)
3. Your API will be available at: `https://your-service-name.onrender.com`

## 🌐 Frontend Deployment (GitHub Pages)

### Step 1: Update API URL
Once your backend is deployed, update the API URL in `dashboard-enhanced.html`:

```javascript
const API_BASE = 'https://your-service-name.onrender.com/api';
```

### Step 2: Deploy to GitHub Pages
1. Go to your repository settings
2. Navigate to **Pages** section
3. Select **"GitHub Actions"** as source
4. The workflow will automatically deploy your dashboard

## 🔗 Final URLs
- **Frontend**: `https://kunjchacha.github.io/Campaign-Inventory/dashboard-enhanced.html`
- **Backend API**: `https://your-service-name.onrender.com/api`

## 🛠️ Troubleshooting

### Common Issues:
1. **Build fails**: Check if all dependencies are in `requirements.txt`
2. **psycopg2 ImportError**: Ensure Python 3.11 is used (not 3.13)
3. **Database connection fails**: Verify environment variables are set correctly
4. **CORS errors**: Ensure CORS is enabled in Flask app
5. **API not responding**: Check Render logs for errors

### Check Logs:
- Render dashboard → Your service → **Logs** tab
- GitHub Actions → **Actions** tab → Your workflow

## 📞 Support
If you encounter issues:
1. Check the logs in Render dashboard
2. Verify environment variables are correct
3. Test database connection locally first
