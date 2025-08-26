#!/usr/bin/env python3
"""
Test script for date conversion function
"""

def convert_excel_date_to_readable(date_value):
    """Convert Excel date number or string date to readable format"""
    if date_value is None:
        return ''
    
    try:
        # If it's already a string date, return as is
        if isinstance(date_value, str):
            # Check if it's already a readable date format
            if any(day in date_value for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']):
                return date_value
            # Check if it's a numeric string (Excel date)
            if date_value.isdigit():
                excel_date = int(date_value)
            else:
                return date_value
        else:
            # If it's a number, treat as Excel date
            excel_date = int(date_value)
        
        # Convert Excel date number to datetime
        # Excel dates are days since January 1, 1900
        from datetime import datetime, timedelta
        excel_epoch = datetime(1900, 1, 1)
        actual_date = excel_epoch + timedelta(days=excel_date - 2)  # -2 for Excel's leap year bug
        
        # Format as "Monday, January 06, 2025"
        return actual_date.strftime('%A, %B %d, %Y')
        
    except Exception as e:
        print(f"Error converting date {date_value}: {e}")
        return str(date_value) if date_value else ''

# Test cases
test_cases = [
    "46027",  # Should convert to a date in 2025
    "46083",  # Should convert to a date in 2025
    "46146",  # Should convert to a date in 2025
    "Monday, January 06, 2025",  # Should remain unchanged
    "Tuesday, August 26, 2025",  # Should remain unchanged
    None,  # Should return empty string
    "",  # Should return empty string
    "invalid_date",  # Should return as is
]

print("Testing date conversion function:")
print("=" * 50)

for test_case in test_cases:
    result = convert_excel_date_to_readable(test_case)
    print(f"Input: {test_case}")
    print(f"Output: {result}")
    print("-" * 30)
