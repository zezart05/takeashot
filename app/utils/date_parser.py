from datetime import datetime, timedelta
import re

def parse_deadline(text: str) -> datetime:
    """Parse natural language deadline into datetime"""
    text = text.lower().strip()
    now = datetime.now()
    today = now.replace(hour=23, minute=59, second=59)
    
    # Direct date formats
    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%d.%m.%Y']:
        try:
            return datetime.strptime(text, fmt).replace(hour=23, minute=59, second=59)
        except:
            pass
    
    # Today/Tomorrow
    if text in ['today', 'tonight']:
        return today
    if text in ['tomorrow', 'tmr', 'tmrw']:
        return today + timedelta(days=1)
    
    # In X days/weeks/months
    match = re.match(r'in\s+(\d+)\s+(day|days|week|weeks|month|months)', text)
    if match:
        num = int(match.group(1))
        unit = match.group(2)
        if 'day' in unit:
            return today + timedelta(days=num)
        elif 'week' in unit:
            return today + timedelta(weeks=num)
        elif 'month' in unit:
            return today + timedelta(days=num*30)
    
    # Day names mapping
    days_of_week = {
        'monday': 0, 'mon': 0,
        'tuesday': 1, 'tue': 1, 'tues': 1,
        'wednesday': 2, 'wed': 2,
        'thursday': 3, 'thu': 3, 'thur': 3, 'thurs': 3,
        'friday': 4, 'fri': 4,
        'saturday': 5, 'sat': 5,
        'sunday': 6, 'sun': 6
    }
    
    # Parse day names with "next" or "this"
    for day_name, day_num in days_of_week.items():
        if day_name in text:
            current_day = now.weekday()
            
            if 'next' in text:
                # Next week's day (skip this week entirely)
                days_ahead = day_num - current_day
                if days_ahead <= 0:
                    days_ahead += 7
                days_ahead += 7  # Add another week for "next"
                return today + timedelta(days=days_ahead)
            
            elif 'this' in text:
                # This week's day (but must be in future)
                days_ahead = day_num - current_day
                if days_ahead <= 0:
                    days_ahead += 7
                return today + timedelta(days=days_ahead)
            
            else:
                # Just day name - find next occurrence
                days_ahead = day_num - current_day
                if days_ahead <= 0:
                    days_ahead += 7
                return today + timedelta(days=days_ahead)
    
    # End of week
    if 'end of week' in text or 'eow' in text:
        days_until_friday = (4 - now.weekday()) % 7
        if days_until_friday == 0 and now.hour >= 18:
            days_until_friday = 7
        return today + timedelta(days=days_until_friday)
    
    # End of month
    if 'end of month' in text or 'eom' in text:
        if now.month == 12:
            next_month = now.replace(year=now.year+1, month=1, day=1)
        else:
            next_month = now.replace(month=now.month+1, day=1)
        return (next_month - timedelta(days=1)).replace(hour=23, minute=59, second=59)
    
    # Next week (means Monday of next week)
    if text == 'next week':
        days_until_monday = (7 - now.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        return today + timedelta(days=days_until_monday)
    
    # X days from now (without "in")
    match = re.match(r'(\d+)\s*days?', text)
    if match:
        return today + timedelta(days=int(match.group(1)))
    
    raise ValueError(f"Could not parse date: {text}")