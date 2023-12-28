from random import choices
import re
from datetime import datetime, timedelta


def labour_productivity_via(*, investment):
    """Find a suitable productivity level of a slave based on the investment"""
    # Set your desired ranges
    lower_limit = 1000
    upper_limit = 5000e7

    # Map the productivity to a 1 to 10 scale
    scaled_productivity = 1 + (investment - lower_limit) / (upper_limit - lower_limit) * 9

    # Ensure the result is within the 1 to 10 range
    ranan = max(1, min(10, scaled_productivity))
    choicess = [0.3, 0.6, 0.9, 1.2, 1.5, 1.8, 2.1]
    multi = choices(choicess,
                           weights=[25, 20, 15, 14, 12, 5, 9])
    return round(ranan+multi[0], 2)


def parse_duration(input_duration):
    # Define regular expression pattern to extract days and hours
    pattern = re.compile(r'(?:(\d+)d)? ?(?:(\d+)h)?')

    # Extract days and hours from the input duration using the pattern
    match = pattern.match(input_duration)

    # Get the number of days and hours from the match
    days = int(match.group(1)) if match.group(1) else 0
    hours = int(match.group(2)) if match.group(2) else 0

    # Check if both days and hours are 0
    if days == 0 and hours == 0:
        raise ValueError("Invalid duration, years-duration and/or seconds-duration is unsupported.")

    # Calculate the timedelta based on the extracted days and hours
    duration = timedelta(days=days, hours=hours)

    # Check if the duration exceeds 14 days
    if duration.days > 14:
        raise ValueError("Duration cannot exceed 14 days.")

    # Get the current datetime
    current_datetime = datetime.now()

    # Calculate the datetime after the specified duration
    res_date = current_datetime + duration

    return res_date

def datetime_to_string(datetime_obj: datetime) -> str:
    """Convert a datetime object to a string object.

    Datetime will be converted to this format: %Y-%m-%d %H:%M:%S"""
    date_format = "%Y-%m-%d %H:%M:%S"
    formatted_string = datetime_obj.strftime(date_format)
    return formatted_string


def string_to_datetime(string_obj: str) -> datetime:
    """Convert a string object to a datetime object.

    String must be in this format: %Y-%m-%d %H:%M:%S

    :param string_obj: the input string representing a date and time.
    :returns: A datetime object."""

    date_format = "%Y-%m-%d %H:%M:%S"
    my_datetime = datetime.strptime(string_obj, date_format)
    return my_datetime
