import React, { useState, useMemo, useCallback, useEffect } from 'react';
import { statusStyles } from './constants';
import type { InventoryItem, Status, DatabaseInventoryItem, CampaignLedgerItem } from './types';
import { ClientsModal } from './components/ClientsModal';
import { ProductDetailCard } from './components/ProductDetailCard';
import { PieChart } from './components/PieChart';
import { ClientModal } from './components/ClientModal';
import { WeeklyView } from './components/WeeklyView';
import { useDatabase } from './hooks/useDatabase';

const formatDateForInput = (date: Date): string => {
    return date.toISOString().split('T')[0];
};

export const App = () => {
  const [selectedBrand, setSelectedBrand] = useState('All');
  const [selectedProduct, setSelectedProduct] = useState('Overall');
  const [isClientsModalOpen, setClientsModalOpen] = useState(false);
  const [isClientModalOpen, setClientModalOpen] = useState(false);
  
  // Date filter state
  const [filterStartDate, setFilterStartDate] = useState<string>('');
  const [filterEndDate, setFilterEndDate] = useState<string>('');
  const [appliedDateRange, setAppliedDateRange] = useState<{ start: string; end: string } | null>(null);
  const [dateError, setDateError] = useState<string>('');

  // Use the database hook
  const { 
    inventoryData: databaseInventory, 
    campaignLedger, 
    brandOverview, 
    previewData, 
    isLoading, 
    error, 
    fetchPreviewData
  } = useDatabase();

  // Extract unique products and brands from database data
  const products = useMemo(() => {
    const uniqueProducts = new Set(databaseInventory.map(item => item.product));
    return Array.from(uniqueProducts).sort();
  }, [databaseInventory]);

  const brands = useMemo(() => {
    const uniqueBrands = new Set(databaseInventory.map(item => item.brand));
    return Array.from(uniqueBrands).sort();
  }, [databaseInventory]);

  // Fetch data on component mount
  useEffect(() => {
    // Fetch initial preview data
    fetchPreviewData(selectedBrand, selectedProduct);
  }, [fetchPreviewData]);

  const handleApplyDateFilter = useCallback(() => {
    if (!filterStartDate || !filterEndDate) {
      setDateError('Please select both a start and end date.');
      return;
    }
    if (new Date(filterStartDate) > new Date(filterEndDate)) {
      setDateError('Start date cannot be after end date.');
      setAppliedDateRange(null);
      return;
    }
    setDateError('');
    setAppliedDateRange({ start: filterStartDate, end: filterEndDate });
    
    // Fetch preview data with current filters
    fetchPreviewData(selectedBrand, selectedProduct, filterStartDate, filterEndDate);
  }, [filterStartDate, filterEndDate, selectedBrand, selectedProduct, fetchPreviewData]);
  
  const handleClearDateFilter = useCallback(() => {
      setFilterStartDate('');
      setFilterEndDate('');
      setAppliedDateRange(null);
      setDateError('');
  }, []);

  const handleManualDateChange = (dateStr: string, type: 'start' | 'end') => {
    if (type === 'start') {
      setFilterStartDate(dateStr);
    } else {
      setFilterEndDate(dateStr);
    }
    
    setDateError('');
  };

  // Filter database inventory based on selections
  const filteredDatabaseInventory = useMemo(() => {
    let filtered = databaseInventory;

    if (selectedBrand !== 'All') {
      filtered = filtered.filter(item => item.brand === selectedBrand);
    }

    if (selectedProduct !== 'Overall') {
      filtered = filtered.filter(item => item.product === selectedProduct);
    }

    if (appliedDateRange) {
      const { start, end } = appliedDateRange;
      const rangeStart = new Date(start + 'T00:00:00');
      const rangeEnd = new Date(end + 'T00:00:00');

      filtered = filtered.filter(item => {
        const itemStart = new Date(item.start_date + 'T00:00:00');
        const itemEnd = new Date(item.end_date + 'T00:00:00');
        return itemStart <= rangeEnd && itemEnd >= rangeStart;
      });
    }

    return filtered;
  }, [databaseInventory, selectedBrand, selectedProduct, appliedDateRange]);

  // Get available brands and products from database
  const availableBrands = useMemo(() => {
    const brands = [...new Set(databaseInventory.map(item => item.brand))];
    return brands.sort();
  }, [databaseInventory]);

  const availableProducts = useMemo(() => {
    const products = [...new Set(databaseInventory.map(item => item.product))];
    return products.sort();
  }, [databaseInventory]);

  const filteredStats = useMemo(() => {
    let filteredData = previewData;

    // Apply date filtering if date range is set
    if (appliedDateRange) {
      const { start, end } = appliedDateRange;
      const rangeStart = new Date(start + 'T00:00:00');
      const rangeEnd = new Date(end + 'T00:00:00');

      filteredData = previewData.filter(item => {
        const dateStr = item.start_date;
        if (!dateStr) return false;
        
        let itemDate: Date | null = null;
        
        // Handle different date formats
        if (typeof dateStr === 'string') {
          // Format: "Monday, August 11, 2025"
          if (dateStr.includes(',')) {
            const datePart = dateStr.split(', ').slice(1).join(', ');
            itemDate = new Date(datePart);
          }
        }
        
        if (!itemDate || isNaN(itemDate.getTime())) return false;
        
        const isInRange = itemDate >= rangeStart && itemDate <= rangeEnd;
        
        return isInRange;
      });
    }

    const stats = {
        booked: filteredData.filter(i => i.status === 'Booked').length,
        onHold: filteredData.filter(i => i.status === 'On Hold').length,
        available: filteredData.filter(i => i.status === 'Available').length,
        total: filteredData.length
    };
    return stats;
  }, [previewData, appliedDateRange]);

  const chartData = useMemo(() => [
      { name: 'Booked' as Status, value: filteredStats.booked, color: statusStyles.Booked.colorHex },
      { name: 'On Hold' as Status, value: filteredStats.onHold, color: statusStyles['On Hold'].colorHex },
      { name: 'Available' as Status, value: filteredStats.available, color: statusStyles.Available.colorHex },
  ], [filteredStats]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-900 text-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-slate-400">Loading database data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-900 text-white flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-400 text-xl mb-4">Error loading data</div>
          <p className="text-slate-400">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700 p-3 sm:p-4">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
            {/* Main Title */}
            <div className="text-center lg:text-left">
              <h1 className="text-xl sm:text-2xl font-bold text-slate-100">📊 Commercial Inventory Dashboard</h1>
              <p className="text-slate-400 text-sm sm:text-base">Track available slots for booking across all brands and products</p>
            </div>
            
            {/* Weekly View - Top Right */}
            <div className="flex justify-center lg:justify-end">
              <WeeklyView className="w-full max-w-xs" />
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto p-3 sm:p-4 md:p-6 lg:p-8">
        {/* Brand Overview Section - Single Graphical View */}
        <section className="mb-6 sm:mb-8">
          <h2 className="text-lg sm:text-xl font-bold text-slate-100 mb-4 sm:mb-6">📈 Brand Overview - Total Inventory</h2>
          <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4 sm:p-6">
            {brands.map(brand => {
              const brandData = brandOverview[brand];
              if (!brandData) return null;
              
              const booked = brandData.booked || 0;
              const onHold = brandData.on_hold || 0;
              const available = brandData.not_booked || 0;
              const total = brandData.total_slots || 0;
              
              const bookedPercent = total > 0 ? (booked / total) * 100 : 0;
              const onHoldPercent = total > 0 ? (onHold / total) * 100 : 0;
              const availablePercent = total > 0 ? (available / total) * 100 : 0;
              
              return (
                <div key={brand} className="mb-4 last:mb-0">
                  <div className="flex justify-between items-center mb-2">
                    <h3 className="font-semibold text-slate-200">{brand}</h3>
                    <span className="text-sm text-slate-400">Total: {total} slots</span>
                  </div>
                  
                  {/* Progress Bar */}
                  <div className="w-full bg-slate-700 rounded-full h-8 relative overflow-hidden">
                    {/* Booked (Green) */}
                    <div 
                      className="h-full bg-green-500 transition-all duration-300 flex items-center justify-center relative"
                      style={{ width: `${bookedPercent}%` }}
                    >
                      {bookedPercent > 10 && (
                        <span className="text-white text-xs font-medium">
                          {Math.round(bookedPercent)}%
                        </span>
                      )}
                    </div>
                    
                    {/* On Hold (Yellow) */}
                    <div 
                      className="h-full bg-yellow-500 transition-all duration-300 flex items-center justify-center relative"
                      style={{ width: `${onHoldPercent}%`, marginLeft: `${bookedPercent}%` }}
                    >
                      {onHoldPercent > 10 && (
                        <span className="text-white text-xs font-medium">
                          {Math.round(onHoldPercent)}%
                        </span>
                      )}
                    </div>
                    
                    {/* Available (Grey) - remaining space */}
                    <div 
                      className="h-full bg-slate-500 transition-all duration-300 flex items-center justify-center relative"
                      style={{ width: `${availablePercent}%`, marginLeft: `${bookedPercent + onHoldPercent}%` }}
                    >
                      {availablePercent > 10 && (
                        <span className="text-white text-xs font-medium">
                          {Math.round(availablePercent)}%
                        </span>
                      )}
                    </div>
                  </div>
                  
                  {/* Counts Legend */}
                  <div className="flex justify-between text-xs text-slate-400 mt-2">
                    <span>Booked: {booked}</span>
                    <span>On Hold: {onHold}</span>
                    <span>Available: {available}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </section>



        {/* --- Commercial Filters --- */}
        <section className="mb-6 sm:mb-8 p-3 sm:p-4 bg-slate-800/50 border border-slate-700 rounded-lg">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-base sm:text-lg font-semibold text-slate-100">🎯 Filters - Find Available Inventory</h2>
            <button
              onClick={() => setClientModalOpen(true)}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition-colors text-sm"
            >
              👥 View Clients
            </button>
          </div>
          
          {/* Filters */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6 gap-3 sm:gap-4">
            {/* Products Dropdown */}
            <div className="sm:col-span-1">
              <label htmlFor="product-filter" className="block text-xs font-medium text-slate-400 mb-1">Products</label>
              <select 
                id="product-filter"
                value={selectedProduct}
                onChange={(e) => {
                  setSelectedProduct(e.target.value);
                  // Remove auto-fetch - user will click Apply Filters
                }}
                className="w-full bg-slate-700 border border-slate-600 rounded-md py-2 px-3 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="Overall">Overall</option>
                {availableProducts.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            
            {/* Brand Dropdown */}
            <div className="sm:col-span-1">
              <label htmlFor="brand-filter" className="block text-xs font-medium text-slate-400 mb-1">Brand</label>
              <select 
                id="brand-filter"
                value={selectedBrand}
                onChange={(e) => {
                  setSelectedBrand(e.target.value);
                  // Remove auto-fetch - user will click Apply Filters
                }}
                className="w-full bg-slate-700 border border-slate-600 rounded-md py-2 px-3 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="All">All Brands</option>
                {brands.map(brand => <option key={brand} value={brand}>{brand}</option>)}
              </select>
            </div>
            
            {/* Date Inputs */}
            <div className="sm:col-span-1">
              <label htmlFor="start-date-filter" className="block text-xs font-medium text-slate-400 mb-1">Start Date</label>
              <input
                type="date"
                id="start-date-filter"
                value={filterStartDate}
                onChange={e => handleManualDateChange(e.target.value, 'start')}
                className="w-full bg-slate-700 border border-slate-600 rounded-md py-2 px-3 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="sm:col-span-1">
              <label htmlFor="end-date-filter" className="block text-xs font-medium text-slate-400 mb-1">End Date</label>
              <input
                type="date"
                id="end-date-filter"
                value={filterEndDate}
                onChange={e => handleManualDateChange(e.target.value, 'end')}
                className="w-full bg-slate-700 border border-slate-600 rounded-md py-2 px-3 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Action Buttons */}
            <div className="flex items-center gap-2 sm:col-span-2">
              <button
                onClick={() => {
                  // Fetch data with current brand, product, and date selections
                  if (filterStartDate && filterEndDate) {
                    fetchPreviewData(selectedBrand, selectedProduct, filterStartDate, filterEndDate);
                    handleApplyDateFilter();
                  } else {
                    fetchPreviewData(selectedBrand, selectedProduct);
                  }
                }}
                className="w-full sm:w-auto bg-blue-600 hover:bg-blue-500 text-white font-bold py-2 px-4 rounded-lg transition-colors">
                Apply Filters
              </button>
              {appliedDateRange && (
                <button
                  onClick={() => {
                    handleClearDateFilter();
                    fetchPreviewData(selectedBrand, selectedProduct);
                  }}
                  className="w-full sm:w-auto bg-slate-600 hover:bg-slate-500 text-white font-bold py-2 px-4 rounded-lg transition-colors">
                  Clear
                </button>
              )}
            </div>
          </div>
          {dateError && <p className="text-red-400 text-sm mt-2">{dateError}</p>}
        </section>
        
        {/* Filtered Inventory Preview Section */}
        <section className="mb-6 sm:mb-8">
          <h2 className="text-lg sm:text-xl font-bold text-slate-100 mb-3 sm:mb-4">
            📊 Filtered Inventory {appliedDateRange && <span className="text-sm sm:text-base font-normal text-slate-400">- ({appliedDateRange.start} to {appliedDateRange.end})</span>}
          </h2>
          
          {previewData.length === 0 ? (
            <div className="text-center py-8 bg-slate-800/50 border border-slate-700 rounded-lg">
              <p className="text-slate-400 text-lg">Click "Apply Filters" to view inventory data</p>
            </div>
          ) : (
            <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-slate-200 mb-6 text-center">
                {selectedProduct === 'Overall' ? 'All Products' : selectedProduct} - {selectedBrand === 'All' ? 'All Brands' : selectedBrand}
              </h3>
              
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">
                {/* Stats Cards */}
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-slate-700/50 rounded-lg p-4 text-center border border-slate-600">
                    <div className="text-3xl font-bold text-green-400 mb-2">
                      {filteredStats.booked}
                    </div>
                    <div className="text-sm text-slate-300 font-medium">Booked</div>
                  </div>
                  <div className="bg-slate-700/50 rounded-lg p-4 text-center border border-slate-600">
                    <div className="text-3xl font-bold text-yellow-400 mb-2">
                      {filteredStats.onHold}
                    </div>
                    <div className="text-sm text-slate-300 font-medium">On Hold</div>
                  </div>
                  <div className="bg-slate-700/50 rounded-lg p-4 text-center border border-slate-600">
                    <div className="text-3xl font-bold text-slate-400 mb-2">
                      {filteredStats.available}
                    </div>
                    <div className="text-sm text-slate-300 font-medium">Available</div>
                  </div>
                </div>
                
                {/* Medium Pie Chart */}
                <div className="flex justify-center">
                  <div className="w-56 h-56">
                    <PieChart title="" data={chartData} />
                  </div>
                </div>
              </div>
              
              {/* Summary */}
              <div className="mt-8 text-center">
                <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-600">
                  <p className="text-slate-200 text-lg">
                    Total: <span className="font-bold text-white">{filteredStats.total}</span> slots | 
                    Utilization: <span className="font-bold text-green-400">
                      {filteredStats.total > 0 ? Math.round((filteredStats.booked / filteredStats.total) * 100) : 0}%
                    </span>
                  </p>
                </div>
              </div>
            </div>
          )}
        </section>
      </div>

      {/* Modals */}
      <ClientsModal 
        isOpen={isClientsModalOpen} 
        onClose={() => setClientsModalOpen(false)} 
      />
      
      <ClientModal
        isOpen={isClientModalOpen}
        onClose={() => setClientModalOpen(false)}
        campaigns={campaignLedger}
        selectedBrand={selectedBrand}
        selectedProduct={selectedProduct}
        appliedDateRange={appliedDateRange}
      />
    </div>
  );
};