/**
 * Utility functions for week calculations
 */

export interface WeekRange {
  startDate: string; // YYYY-MM-DD format
  endDate: string;   // YYYY-MM-DD format
  weekLabel: string; // e.g., "Week of Sep 8, 2025"
}

/**
 * Calculate the next week (Monday to Sunday) based on current date
 * @param currentDate - The current date (defaults to today)
 * @returns WeekRange object with start/end dates and label
 */
export function getNextWeek(currentDate: Date = new Date()): WeekRange {
  // Get the date of next Monday
  const nextMonday = getNextMonday(currentDate);
  
  // Calculate Sunday (6 days after Monday)
  const nextSunday = new Date(nextMonday);
  nextSunday.setDate(nextMonday.getDate() + 6);
  
  return {
    startDate: formatDateForAPI(nextMonday),
    endDate: formatDateForAPI(nextSunday),
    weekLabel: formatWeekLabel(nextMonday)
  };
}

/**
 * Get the date of the next Monday from a given date
 */
function getNextMonday(date: Date): Date {
  const dayOfWeek = date.getDay(); // 0 = Sunday, 1 = Monday, ..., 6 = Saturday
  const daysUntilMonday = dayOfWeek === 0 ? 1 : (8 - dayOfWeek) % 7; // Handle Sunday case
  
  const nextMonday = new Date(date);
  nextMonday.setDate(date.getDate() + daysUntilMonday);
  
  return nextMonday;
}

/**
 * Format date for API calls (YYYY-MM-DD)
 */
function formatDateForAPI(date: Date): string {
  return date.toISOString().split('T')[0];
}

/**
 * Format week label for display
 */
function formatWeekLabel(mondayDate: Date): string {
  const options: Intl.DateTimeFormatOptions = { 
    month: 'short', 
    day: 'numeric', 
    year: 'numeric' 
  };
  return `Week of ${mondayDate.toLocaleDateString('en-US', options)}`;
}

/**
 * Check if a date falls within a week range
 */
export function isDateInWeekRange(date: string, weekRange: WeekRange): boolean {
  const checkDate = new Date(date);
  const startDate = new Date(weekRange.startDate);
  const endDate = new Date(weekRange.endDate);
  
  return checkDate >= startDate && checkDate <= endDate;
}
