# 🎯 Product Breakdown Threshold Configuration

## 📊 **Easy Configuration**

To change the booking percentage threshold for product display, simply edit the `constants/productBreakdown.ts` file:

```typescript
export const PRODUCT_BREAKDOWN_CONFIG = {
  // Change this value to adjust the threshold
  MIN_BOOKING_PERCENTAGE: 7,  // ← Change this number
  // ... rest of config
} as const;
```

## 🔧 **Examples**

### Change to 5% threshold:
```typescript
MIN_BOOKING_PERCENTAGE: 5,
```

### Change to 10% threshold:
```typescript
MIN_BOOKING_PERCENTAGE: 10,
```

### Change to 15% threshold:
```typescript
MIN_BOOKING_PERCENTAGE: 15,
```

## ⚡ **How It Works**

1. **Dynamic Updates**: Products automatically appear/disappear based on current booking percentage
2. **Real-time**: Updates every 30 seconds when modal is open
3. **Threshold Logic**: Shows products with booking rate ≥ (greater than or equal to) the threshold
4. **Automatic Messages**: Note text and empty state messages update automatically

## 📝 **What Updates Automatically**

- ✅ Product list (shows/hides products based on threshold)
- ✅ Note text ("Only products with booking rates above X%...")
- ✅ Empty state messages ("No products meet the X% threshold...")
- ✅ All text references to the threshold value

## 🚀 **No Code Changes Needed**

Once you change the `MIN_BOOKING_PERCENTAGE` value:
- ✅ All text updates automatically
- ✅ Filtering logic updates automatically  
- ✅ UI messages update automatically
- ✅ No need to search/replace text in components

## 🔄 **Current Behavior**

- **Threshold**: ≥7% (greater than or equal to 7%)
- **Update Frequency**: Every 30 seconds when modal is open
- **Display**: Products appear immediately when they cross the threshold
- **Empty State**: Shows helpful message when no products meet threshold

## 📱 **Testing**

1. Open the Product Breakdown modal
2. Change the threshold in `constants/productBreakdown.ts`
3. Save the file
4. The modal will update automatically on the next refresh cycle
5. Products will appear/disappear based on the new threshold

---

**That's it! Just change one number and everything updates automatically! 🎉**
