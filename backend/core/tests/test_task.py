from datetime import date, datetime, timedelta
from dateutil import relativedelta as rd

# Import functions to be tested from core.utils
from core.utils import (
    _convert_to_python_weekday,
    _get_month_range,
    _get_nth_weekday_of_month,
    _date_matches_schedule,
    _calculate_next_occurrence,
    _create_task_dict,
    _generate_occurrences,
)


# --- Fake classes to simulate task objects and their relationships ---
# class DummyQuerySet:
#     """Simulates a queryset returning a list of simple objects with an 'id' attribute."""

#     def __init__(self, ids):
#         self.items = [DummyObject(_id) for _id in ids]

#     def all(self):
#         return self.items


# class DummyObject:
#     def __init__(self, _id):
#         self.id = _id


# class DummyTask:
#     """
#     Simulates a task or template object.
#     Minimum required attributes:
#         - id, name, description, ref_id, task_date, due_date, schedule
#         - assigned_to, assets, applied_controls, compliance_assessments, risk_assessments
#     """

#     def __init__(self, **kwargs):
#         self.id = kwargs.get("id", 1)
#         self.name = kwargs.get("name", "Dummy Task")
#         self.description = kwargs.get("description", "Description")
#         self.ref_id = kwargs.get("ref_id", "ref1")
#         self.task_date = kwargs.get("task_date")  # Must be a date or string
#         self.due_date = kwargs.get("due_date")  # Must be a date or None
#         self.schedule = kwargs.get("schedule", {})
#         self.is_recurrent = kwargs.get("is_recurrent", True)
#         # Relations are simulated by DummyQuerySet
#         self.assigned_to = DummyQuerySet(kwargs.get("assigned_to", [1]))
#         self.assets = DummyQuerySet(kwargs.get("assets", [10]))
#         self.applied_controls = DummyQuerySet(kwargs.get("applied_controls", [20]))
#         self.compliance_assessments = DummyQuerySet(
#             kwargs.get("compliance_assessments", [30])
#         )
#         self.risk_assessments = DummyQuerySet(kwargs.get("risk_assessments", [40]))


# --- Tests of utility functions ---


def test_convert_to_python_weekday():
    # Checks conversion from 0=Sunday to 0=Monday
    # Example: If day=0 (Sunday) then (_convert_to_python_weekday(0)) should return 6 (since Monday=0,...,Sunday=6)
    assert _convert_to_python_weekday(0) == 6
    # For day=1 (Monday) -> 0
    assert _convert_to_python_weekday(1) == 0
    # For day=3 (Wednesday) -> 2
    assert _convert_to_python_weekday(3) == 2


def test_get_month_range():
    # For March 2025, the first day should be March 1 and the last day March 31
    first_day, last_day = _get_month_range(2025, 3)
    assert first_day == date(2025, 3, 1)
    assert last_day == date(2025, 3, 31)

    # For February 2024 (leap year) the last day should be February 29
    _, last_day_feb = _get_month_range(2024, 2)
    assert last_day_feb == date(2024, 2, 29)


def test_get_nth_weekday_of_month_positive():
    # For April 2025, find the 2nd Tuesday.
    # In our system, weekday is based on Python (0=Monday,...,6=Sunday).
    # Tuesday corresponds to 1 (Monday=0, Tuesday=1). The first Tuesday in April 2025 is April 1,
    # so the 2nd Tuesday is April 8.
    nth_tuesday = _get_nth_weekday_of_month(2025, 4, 1, 2)
    assert nth_tuesday == date(2025, 4, 8)


def test_get_nth_weekday_of_month_negative():
    # For April 2025, find the last Friday.
    # In Python, Friday corresponds to 4 (Monday=0,...,Friday=4)
    last_friday = _get_nth_weekday_of_month(2025, 4, 4, -1)
    # The last Friday in April 2025 is April 25
    assert last_friday == date(2025, 4, 25)


# --- Tests of _date_matches_schedule ---


# def test_date_matches_schedule_daily():
#     # For a daily recurring task, all days match
#     schedule = {"frequency": "DAILY"}
#     dummy = DummyTask(schedule=schedule)
#     test_date = date(2025, 5, 15)
#     assert _date_matches_schedule(dummy, test_date)


# def test_date_matches_schedule_weekly():
#     # For a weekly task, test matching of weekdays.
#     # Suppose schedule.days_of_week contains the number 2 (which represents Tuesday in our system, since:
#     # adjusted_weekday = (date.weekday()+1)%7, so for Tuesday, date.weekday()=1, adjusted_weekday=2).
#     schedule = {"frequency": "WEEKLY", "days_of_week": [2]}
#     dummy = DummyTask(schedule=schedule)

#     # Create a date that is a Tuesday: for example, June 13, 2025 which is a Friday? Check via date.weekday()
#     # To be sure, use a known Tuesday date: June 11, 2025 (which is a Wednesday according to date.weekday()? Verify)
#     # Rather, build a date and verify its conversion.
#     # For a date where date.weekday()+1 %7 == 2, it must be that date.weekday() == 1 (it's Tuesday).
#     tuesday = date(
#         2025, 6, 3
#     )  # June 3, 2025 is a Tuesday (verifiable via calendar.weekday)
#     assert tuesday.weekday() == 1  # Tuesday
#     assert _date_matches_schedule(dummy, tuesday)

#     # A date that is not Tuesday should not match
#     wednesday = date(2025, 6, 4)
#     assert not _date_matches_schedule(dummy, wednesday)


# def test_date_matches_schedule_monthly():
#     # For a monthly task with restrictions on the weekday and week of the month.
#     # For example, the 2nd occurrence of Thursday of the month.
#     # In our system, Thursday in adjusted_day is: Thursday in Python is 3 (Monday=0,...)
#     # Adjusted: (3+1)%7 = 4, so we put 4 in days_of_week.
#     schedule = {"frequency": "MONTHLY", "days_of_week": [4], "weeks_of_month": [2]}
#     dummy = DummyTask(schedule=schedule)

#     # For June 2025, the 2nd Thursday is June 12, 2025.
#     test_date = date(2025, 6, 12)
#     assert _date_matches_schedule(dummy, test_date)

#     # Another date in the month that is not the 2nd Thursday should not match
#     wrong_date = date(2025, 6, 19)  # 3rd Thursday
#     assert not _date_matches_schedule(dummy, wrong_date)


# def test_date_matches_schedule_yearly():
#     # For an annual task with restrictions on the month and weekday.
#     # For example, only April, the 1st Sunday.
#     # To get Sunday in adjusted_day: in Python, Sunday is 6, so (6+1)%7 == 0.
#     schedule = {
#         "frequency": "YEARLY",
#         "months_of_year": [4],
#         "days_of_week": [0],
#         "weeks_of_month": [1],
#     }
#     dummy = DummyTask(schedule=schedule)

#     # For April 2025, the first Sunday is April 6, 2025.
#     test_date = date(2025, 4, 6)
#     assert _date_matches_schedule(dummy, test_date)

#     # Another day in April should not match
#     wrong_date = date(2025, 4, 13)
#     assert not _date_matches_schedule(dummy, wrong_date)


# # --- Tests of _calculate_next_occurrence ---


# def test_calculate_next_occurrence_daily():
#     # For a daily task, the next occurrence is simply the next day
#     schedule = {"frequency": "DAILY"}
#     dummy = DummyTask(schedule=schedule)
#     base = date(2025, 7, 20)
#     next_date = _calculate_next_occurrence(dummy, base)
#     assert next_date == base + timedelta(days=1)


# def test_calculate_next_occurrence_weekly():
#     # For a weekly task with specified days.
#     # For example, if days_of_week=[2] (Tuesday in our system),
#     # And the base date is a Monday (date.weekday() == 0, adjusted=1), the next occurrence should be Tuesday.
#     schedule = {"frequency": "WEEKLY", "days_of_week": [2]}
#     dummy = DummyTask(schedule=schedule)
#     # Create a base date that is Monday
#     base = date(2025, 8, 4)  # August 4, 2025, verify that it's a Monday
#     assert base.weekday() == 0
#     next_date = _calculate_next_occurrence(dummy, base)
#     # The expected next occurrence is Tuesday, August 5, 2025
#     assert next_date == date(2025, 8, 5)


# def test_calculate_next_occurrence_monthly():
#     # For a monthly task that specifies the 2nd occurrence of a Tuesday (in adjusted system, Tuesday=2).
#     schedule = {"frequency": "MONTHLY", "days_of_week": [2], "weeks_of_month": [2]}
#     dummy = DummyTask(schedule=schedule)
#     # Choose a base date within a given month, for example June 5, 2025.
#     base = date(2025, 6, 5)
#     # For June 2025, the 2nd Tuesday is June 10, 2025.
#     next_date = _calculate_next_occurrence(dummy, base)
#     assert next_date == date(2025, 6, 10)


# def test_calculate_next_occurrence_yearly():
#     # For an annual task with no additional restrictions, the next occurrence is one year later.
#     schedule = {"frequency": "YEARLY"}
#     dummy = DummyTask(schedule=schedule, task_date="2025-01-01")
#     base = date(2025, 1, 1)
#     next_date = _calculate_next_occurrence(dummy, base)
#     assert next_date == base + rd.relativedelta(years=1)


# # --- Test of _create_task_dict ---


# def test_create_task_dict():
#     # Create a dummy task with reference dates for testing _create_task_dict.
#     task_date = date(2025, 9, 15)
#     due_date = date(2025, 9, 20)
#     dummy = DummyTask(
#         id=99,
#         name="Test Task",
#         description="A test task",
#         ref_id="ref-99",
#         task_date=task_date,
#         due_date=due_date,
#     )
#     # Generate the dictionary for iteration 0
#     task_dict = _create_task_dict(dummy, task_date, 0)

#     assert task_dict["id"] == 99
#     assert task_dict["name"] == "Test Task"
#     assert task_dict["task_date"] == task_date.isoformat()
#     # The difference between due_date and task_date is preserved
#     expected_due_date = (task_date + (due_date - task_date)).isoformat()
#     assert task_dict["due_date"] == expected_due_date
#     # Verify that Many-to-Many relations are correctly transformed
#     assert isinstance(task_dict["assigned_to"], list)
#     assert isinstance(task_dict["assets"], list)
#     assert isinstance(task_dict["applied_controls"], list)
#     assert isinstance(task_dict["compliance_assessments"], list)
#     assert isinstance(task_dict["risk_assessments"], list)


# # --- Tests of occurrence generation and task calendar ---


# def test_generate_occurrences_daily():
#     # Verifies that a daily recurring task generates multiple occurrences within the given range.
#     schedule = {"frequency": "DAILY", "occurrences": 3}
#     # For testing, fix task_date as the starting point.
#     start_date = date(2025, 10, 1)
#     dummy = DummyTask(schedule=schedule, task_date=start_date)
#     # Generate occurrences between October 1 and October 10, 2025
#     occurrences = _generate_occurrences(dummy, date(2025, 10, 1), date(2025, 10, 10))
#     # Should generate 3 occurrences
#     assert len(occurrences) == 3
#     # Verify that the generated dates are consecutive
#     dates = [datetime.fromisoformat(task["task_date"]).date() for task in occurrences]
#     assert dates == sorted(dates)
#     for i in range(1, len(dates)):
#         assert dates[i] - dates[i - 1] == timedelta(days=1)


# def test_task_calendar():
#     # Tests the task_calendar function with a list of templates.
#     # Define a task template with an end recurrence and a task_date.
#     schedule = {
#         "frequency": "WEEKLY",
#         "days_of_week": [2],  # Tuesday (adjusted_day 2)
#         "occurrences": 2,
#         "end_date": "2025-12-31",
#     }
#     template = DummyTask(schedule=schedule, task_date=date(2025, 11, 1))
#     tasks = task_calendar([template])

#     # The function should return a set of future tasks
#     assert isinstance(tasks, list)
#     # Since we limited to 2 occurrences in the schedule, we expect to get 2 tasks
#     assert len(tasks) == 2
#     # Verify that the generated dates are after the start date and sorted
#     task_dates = [datetime.fromisoformat(t["task_date"]).date() for t in tasks]
#     assert all(d > date(2025, 11, 1) for d in task_dates)
#     assert task_dates == sorted(task_dates)
