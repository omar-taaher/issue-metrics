"""A module for calculating duration between two datetime objects with considering business days only.


Functions:
    business_duration(
        start: datetime,
        end: datetime
    ) -> timedelta:
        Calculate the business duration between two datetime objects.

"""

from datetime import datetime, timedelta


def business_duration(start: datetime, end: datetime) -> timedelta:
    # Define the working day start and end time
    workday_start = 9  # 9 AM
    workday_end = 18   # 6 PM

    # Initialize the total duration
    total_duration = timedelta()

    # Loop through each day from start to end
    current = start
    while current < end:
        # Skip non-working days (Friday=4, Saturday=5)
        if current.weekday() in [4, 5]:
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
