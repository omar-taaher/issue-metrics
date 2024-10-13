"""A module for calculating duration between two datetime objects with considering business days only.


Functions:
    business_duration(
        start: datetime,
        end: datetime
    ) -> timedelta:
        Calculate the business duration between two datetime objects.

"""

from datetime import datetime, timedelta
import os



def business_duration(start: datetime, end: datetime) -> timedelta:
    # # Define the working day start and end time
    # workday_start = 9  # 9 AM
    # workday_end = 18   # 6 PM

    # Get the working_hours_start & working_hours_end inputs
    workday_start = int(os.getenv('INPUT_WORKING_HOURS_START', 9))
    workday_end = int(os.getenv('INPUT_WORKING_HOURS_END', 18))

    # Validate the working hours
    if workday_start < 0 or workday_start > 23:
        raise ValueError('Working hours start time must be between 0 and 23')
    if workday_end < 0 or workday_end > 23:
        raise ValueError('Working hours end time must be between 0 and 23')
    if workday_start >= workday_end:
        raise ValueError('Working hours start time must be before the end time')

    # Get the weekend_days input
    weekend_days = os.getenv('INPUT_WEEKEND_DAYS', 'Saturday,Sunday')

    # Split the string into a list of days
    weekend_days_list = [day.strip() for day in weekend_days.split(',')]

    # Define valid days
    valid_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    # Filter out any invalid day names
    filtered_weekend_days = [day for day in weekend_days_list if day in valid_days]
    #Prepare weekend days as integers (0=Monday, 1=Tuesday, ..., 6=Sunday)
    weekend_days_int = [valid_days.index(day) for day in filtered_weekend_days]

    # Initialize the total duration
    total_duration = timedelta()

    # Loop through each day from start to end
    current = start
    while current < end:
        # Skip non-working days
        if current.weekday() in weekend_days_int:
            current += timedelta(days=1)
            current = current.replace(hour=workday_start, minute=0, second=0, microsecond=0)
            continue
        
        # Get the current day work start and end time
        current_start = current.replace(hour=workday_start, minute=0, second=0, microsecond=0)
        current_end = current.replace(hour=workday_end, minute=0, second=0, microsecond=0)
        
        # If current day is the start day, adjust the start time
        if current.date() == start.date():
            current_start = max(current, current_start)
        
        # If current day is the end day, adjust the end time
        if current.date() == end.date():
            current_end = min(end, current_end)

        # Calculate the time spent within working hours
        if current_start < current_end:
            total_duration += current_end - current_start

        # Move to the next day
        current += timedelta(days=1)
        current = current.replace(hour=workday_start, minute=0, second=0, microsecond=0)    
    return total_duration
