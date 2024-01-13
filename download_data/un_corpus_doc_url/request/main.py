import datetime


def get_weekly_date_ranges_adjusted(start_date_str, end_date_str):
    try:
        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d")
    except ValueError:
        print("Invalid date format. Use YYYY-MM-DD.")
        return []

    result_list = []

    # Adjust start_date to the first day of the week (Monday)
    start_day_of_week = start_date.weekday()  # Monday is 0, Sunday is 6
    start_of_week = start_date - datetime.timedelta(days=start_day_of_week)

    while start_of_week < end_date:
        end_of_week = start_of_week + datetime.timedelta(days=6)  # End of the week

        # Adjust the start and end of the week to be within the given date range
        actual_start = max(start_of_week, start_date)
        actual_end = min(end_of_week, end_date)

        result_list.append(
            (actual_start.strftime("%Y-%m-%d"), actual_end.strftime("%Y-%m-%d"))
        )

        # Move to the next week
        start_of_week = end_of_week + datetime.timedelta(days=1)

    return result_list