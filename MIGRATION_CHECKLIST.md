# 📋 **GitHub Migration Checklist: Personal → Office Account**

## 🎯 **Migration Details**
- **From**: `Kunjchacha/Campaign-Inventory` (Personal)
- **To**: `KunjChachaClickZ/Campaign-Inventory` (Office)
- **New Frontend URL**: `https://kunjchachaclickz.github.io/Campaign-Inventory/`
- **Backend**: `https://campaign-inventory-api.onrender.com` (Unchanged)

---

## ✅ **Phase 1: Pre-Migration Preparation**

### **1.1 Backup & Documentation**
- [x] **Create backup of current repository**
  ```bash
  git clone https://github.com/Kunjchacha/Campaign-Inventory.git campaign-inventory-backup
  ```
- [x] **Document current URLs**
  - Current Frontend: `https://kunjchacha.github.io/Campaign-Inventory/`
  - Current Backend: `https://campaign-inventory-api.onrender.com`
  - Current Repository: `https://github.com/Kunjchacha/Campaign-Inventory`

### **1.2 Verify New Repository**
- [x] **Confirm new repository exists**: ✅ `https://github.com/KunjChachaClickZ/Campaign-Inventory.git`
- [x] **Verify repository is empty** (as expected)
- [x] **Check repository visibility** (Public/Private as needed)

---

## ✅ **Phase 2: Code Updates**

### **2.1 Update Repository References**

#### **package.json** (Line 5)
- [x] **Current**: `"homepage": "https://Kunjchacha.github.io/Campaign-Inventory"`
- [x] **Update to**: `"homepage": "https://kunjchachaclickz.github.io/Campaign-Inventory"`

#### **README.md** (Lines 59, 131)
- [x] **Current**: `https://kunjchacha.github.io/Campaign-Inventory/`
- [x] **Update to**: `https://kunjchachaclickz.github.io/Campaign-Inventory/`

#### **DEPLOYMENT.md** (Lines 13, 53)
- [x] **Current**: `Kunjchacha/Campaign-Inventory`
- [x] **Update to**: `KunjChachaClickZ/Campaign-Inventory`
- [x] **Current**: `https://kunjchacha.github.io/Campaign-Inventory/dashboard-enhanced.html`
- [x] **Update to**: `https://kunjchachaclickz.github.io/Campaign-Inventory/dashboard-enhanced.html`

### **2.2 Update Git Remote**
- [x] **Remove current remote**
  ```bash
  git remote remove origin
  ```
- [x] **Add new office repository as remote**
  ```bash
  git remote add origin https://github.com/KunjChachaClickZ/Campaign-Inventory.git
  ```
- [x] **Verify remote**
  ```bash
  git remote -v
  ```

---

## ✅ **Phase 3: Backend Verification**

### **3.1 Render.com Service**
- [x] **Confirm service name**: `campaign-inventory-api`
- [x] **Verify service is running**: ✅ `https://campaign-inventory-api.onrender.com`
- [x] **Test API endpoint**: `GET /api/inventory`
- [x] **Check environment variables** (Database credentials)
- [x] **Verify CORS settings** (Allow GitHub Pages domain)

### **3.2 Database Connection**
- [x] **Confirm database connectivity**
- [x] **Test data retrieval**
- [x] **Verify date conversion working**

---

## ✅ **Phase 4: Code Migration**

### **4.1 Commit Changes**
- [ ] **Stage all changes**
  ```bash
  git add .
  ```
- [ ] **Commit migration changes**
  ```bash
  git commit -m "Migrate to office GitHub account - Update repository references"
  ```

### **4.2 Push to New Repository**
- [ ] **Push to office repository**
  ```bash
  git push -u origin main
  ```
- [ ] **Verify push successful**
- [ ] **Check repository contents**

---

## ✅ **Phase 5: Frontend Deployment**

### **5.1 GitHub Pages Configuration**
- [ ] **Go to**: `https://github.com/KunjChachaClickZ/Campaign-Inventory/settings/pages`
- [ ] **Source**: Deploy from a branch
- [ ] **Branch**: `main`
- [ ] **Folder**: `/ (root)`
- [ ] **Save settings**

### **5.2 GitHub Actions Verification**
- [ ] **Check workflow file**: `.github/workflows/deploy.yml`
- [ ] **Verify workflow runs automatically**
- [ ] **Check deployment status**

### **5.3 Test New Frontend URL**
- [ ] **Access**: `https://kunjchachaclickz.github.io/Campaign-Inventory/dashboard-enhanced.html`
- [ ] **Verify page loads**
- [ ] **Check console for errors**

---

## ✅ **Phase 6: Functionality Testing**

### **6.1 Core Features**
- [ ] **Brand Overview section loads**
- [ ] **Summary cards display data**
- [ ] **Product dropdown works**
- [ ] **Brand dropdown works**
- [ ] **Date range filtering works**
- [ ] **Status filtering works**

### **6.2 API Integration**
- [ ] **Data loads from backend**
- [ ] **Filters send correct parameters**
- [ ] **Date conversion displays properly**
- [ ] **Real-time updates work**

### **6.3 Cross-browser Testing**
- [ ] **Chrome**: ✅
- [ ] **Firefox**: ⏳
- [ ] **Safari**: ⏳
- [ ] **Edge**: ⏳

---

## ✅ **Phase 7: Post-Migration Verification**

### **7.1 URL Testing**
- [ ] **Main dashboard**: `https://kunjchachaclickz.github.io/Campaign-Inventory/dashboard-enhanced.html`
- [ ] **Landing page**: `https://kunjchachaclickz.github.io/Campaign-Inventory/`
- [ ] **API connectivity**: Backend responds correctly

### **7.2 Performance Check**
- [ ] **Page load time**: < 3 seconds
- [ ] **API response time**: < 2 seconds
- [ ] **Data rendering**: Smooth

### **7.3 Error Handling**
- [ ] **Network errors**: Graceful handling
- [ ] **API errors**: User-friendly messages
- [ ] **Empty results**: Clear messaging

---

## ✅ **Phase 8: Cleanup & Documentation**

### **8.1 Archive Personal Repository**
- [ ] **Go to**: `https://github.com/Kunjchacha/Campaign-Inventory/settings`
- [ ] **Scroll to**: "Danger Zone"
- [ ] **Click**: "Archive this repository"
- [ ] **Confirm**: Archive

### **8.2 Update Documentation**
- [ ] **Update README.md** with new URLs
- [ ] **Update DEPLOYMENT.md** with new instructions
- [ ] **Create team access** (if needed)
- [ ] **Update bookmarks** and links

### **8.3 Final Verification**
- [ ] **All tests pass**
- [ ] **No broken links**
- [ ] **Team can access new repository**
- [ ] **Backup repository created**

---

## 🚨 **Rollback Plan**

### **If Issues Occur:**
1. **Immediate Rollback**:
   ```bash
   git remote add origin https://github.com/Kunjchacha/Campaign-Inventory.git
   git push origin main
   ```

2. **Use Backup Repository**:
   ```bash
   cd campaign-inventory-backup
   git remote add origin https://github.com/KunjChachaClickZ/Campaign-Inventory.git
   git push -u origin main
   ```

3. **Recreate from Scratch** (Last Resort)

---

## 📊 **Migration Status Tracker**

| Phase | Status | Completed By | Notes |
|-------|--------|--------------|-------|
| Phase 1 | ⏳ Pending | - | Pre-migration prep |
| Phase 2 | ⏳ Pending | - | Code updates |
| Phase 3 | ⏳ Pending | - | Backend verification |
| Phase 4 | ⏳ Pending | - | Code migration |
| Phase 5 | ⏳ Pending | - | Frontend deployment |
| Phase 6 | ⏳ Pending | - | Functionality testing |
| Phase 7 | ⏳ Pending | - | Post-migration verification |
| Phase 8 | ⏳ Pending | - | Cleanup & documentation |

---

## 🎯 **Success Criteria**

### **Migration Complete When:**
- [ ] New frontend URL works: `https://kunjchachaclickz.github.io/Campaign-Inventory/`
- [ ] All dashboard features function correctly
- [ ] API connectivity maintained
- [ ] No broken links or references
- [ ] Personal repository archived
- [ ] Team has access to new repository

---

## 📞 **Support & Troubleshooting**

### **Common Issues:**
1. **GitHub Pages not loading**: Check repository settings and workflow
2. **API connectivity issues**: Verify Render.com service status
3. **CORS errors**: Check backend CORS configuration
4. **404 errors**: Verify file paths and GitHub Pages configuration

### **Emergency Contacts:**
- **GitHub Support**: For repository issues
- **Render.com Support**: For backend issues
- **Database Admin**: For database connectivity issues

---

**Last Updated**: August 26, 2025  
**Migration Target**: KunjChachaClickZ/Campaign-Inventory  
**Status**: Ready to Begin ⏳
