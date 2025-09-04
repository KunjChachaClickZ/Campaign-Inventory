import React, { useState, useEffect } from 'react';
import { getNextWeek, type WeekRange } from '../utils/weekCalculation';

interface WeeklyComparisonData {
  week_range: {
    start_date: string;
    end_date: string;
  };
  summary: {
    total_booked: number;
    total_form_submissions: number;
  };
  by_brand: {
    [brand: string]: {
      booked: number;
      form_submissions: number;
    };
  };
}

interface WeeklyViewProps {
  className?: string;
}

export const WeeklyView: React.FC<WeeklyViewProps> = ({ className = '' }) => {
  const [weekRange, setWeekRange] = useState<WeekRange | null>(null);
  const [comparisonData, setComparisonData] = useState<WeeklyComparisonData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Calculate next week on component mount
    const nextWeek = getNextWeek();
    setWeekRange(nextWeek);
    
    // Fetch comparison data
    fetchWeeklyComparison(nextWeek);
  }, []);

  const fetchWeeklyComparison = async (week: WeekRange) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(
        `/api/weekly-comparison?start_date=${week.startDate}&end_date=${week.endDate}`
      );
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setComparisonData(data);
    } catch (err) {
      console.error('Error fetching weekly comparison:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusColor = (booked: number, formSubmissions: number) => {
    if (formSubmissions === 0) return 'text-gray-400';
    if (booked === formSubmissions) return 'text-green-400';
    if (booked > formSubmissions) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getStatusIcon = (booked: number, formSubmissions: number) => {
    if (formSubmissions === 0) return '⚪';
    if (booked === formSubmissions) return '✅';
    if (booked > formSubmissions) return '⚠️';
    return '❌';
  };

  if (!weekRange) {
    return (
      <div className={`bg-gray-800 rounded-lg p-4 ${className}`}>
        <div className="animate-pulse">
          <div className="h-4 bg-gray-700 rounded w-3/4 mb-2"></div>
          <div className="h-3 bg-gray-700 rounded w-1/2"></div>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-gray-800 rounded-lg p-4 border border-gray-700 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-blue-400">📅 Weekly Overview</h3>
        <span className="text-xs text-gray-400">{weekRange.weekLabel}</span>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="space-y-2">
          <div className="animate-pulse">
            <div className="h-3 bg-gray-700 rounded w-full mb-1"></div>
            <div className="h-3 bg-gray-700 rounded w-3/4 mb-1"></div>
            <div className="h-3 bg-gray-700 rounded w-1/2"></div>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="text-red-400 text-xs">
          <div className="flex items-center gap-1">
            <span>❌</span>
            <span>Error loading data</span>
          </div>
        </div>
      )}

      {/* Data Display */}
      {comparisonData && !isLoading && !error && (
        <div className="space-y-3">
          {/* Summary */}
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="bg-gray-700 rounded p-2">
              <div className="text-gray-300">Booked</div>
              <div className="text-lg font-bold text-green-400">
                {comparisonData.summary.total_booked}
              </div>
            </div>
            <div className="bg-gray-700 rounded p-2">
              <div className="text-gray-300">Form Filled</div>
              <div className="text-lg font-bold text-blue-400">
                {comparisonData.summary.total_form_submissions}
              </div>
            </div>
          </div>

          {/* By Brand */}
          <div className="space-y-1">
            <div className="text-xs text-gray-400 font-medium">By Brand:</div>
            {Object.entries(comparisonData.by_brand).map(([brand, data]) => (
              <div key={brand} className="flex items-center justify-between text-xs">
                <span className="text-gray-300">{brand}</span>
                <div className="flex items-center gap-2">
                  <span className="text-green-400">{data.booked}</span>
                  <span className="text-gray-500">/</span>
                  <span className="text-blue-400">{data.form_submissions}</span>
                  <span className={getStatusColor(data.booked, data.form_submissions)}>
                    {getStatusIcon(data.booked, data.form_submissions)}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Legend */}
          <div className="text-xs text-gray-500 pt-2 border-t border-gray-700">
            <div className="flex items-center gap-4">
              <span>✅ Synced</span>
              <span>⚠️ Partial</span>
              <span>❌ Missing</span>
            </div>
          </div>
        </div>
      )}

      {/* Empty State */}
      {comparisonData && !isLoading && !error && 
       comparisonData.summary.total_booked === 0 && 
       comparisonData.summary.total_form_submissions === 0 && (
        <div className="text-center text-gray-400 text-xs py-4">
          <div>📅</div>
          <div>No data for this week</div>
        </div>
      )}
    </div>
  );
};
