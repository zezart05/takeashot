from datetime import datetime, timedelta
import re

def parse_deadline(input_str: str) -> datetime:
    """Parse natural language deadline into datetime"""
    input_lower = input_str.lower().strip()
    now = datetime.now()
    
    # Handle "today"
    if "today" in input_lower:
        return now.replace(hour=23, minute=59, second=59)
    
    # Handle "tomorrow"
    if "tomorrow" in input_lower:
        return (now + timedelta(days=1)).replace(hour=23, minute=59, second=59)
    
    # Handle "in X days"
    days_match = re.search(r'in (\d+) days?', input_lower)
    if days_match:
        days = int(days_match.group(1))
        return (now + timedelta(days=days)).replace(hour=23, minute=59, second=59)
    
    # Handle "in X weeks"
    weeks_match = re.search(r'in (\d+) weeks?', input_lower)
    if weeks_match:
        weeks = int(weeks_match.group(1))
        return (now + timedelta(weeks=weeks)).replace(hour=23, minute=59, second=59)
    
    # Handle "next week"
    if "next week" in input_lower:
        return (now + timedelta(days=7)).replace(hour=23, minute=59, second=59)
    
    # Try parsing as a date
    try:
        from dateutil import parser
        parsed_date = parser.parse(input_str, fuzzy=True)
        if parsed_date.hour == 0 and parsed_date.minute == 0:
            parsed_date = parsed_date.replace(hour=23, minute=59, second=59)
        return parsed_date
    except:
        pass
    
    # Default: 7 days from now
    return (now + timedelta(days=7)).replace(hour=23, minute=59, second=59)