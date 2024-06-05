from calendar import LocaleHTMLCalendar
from core.models import AppliedControl, RiskAcceptance
from django.utils.html import format_html


class Calendar(LocaleHTMLCalendar):
    def __init__(self, year=None, month=None, *args, **kwargs):
        self.year = year
        self.month = month
        super(Calendar, self).__init__(*args, **kwargs)

    # formats a day as a td
    # filter events by day
    def formatday(self, day, events):
        events_per_day = list(events["mtg"].filter(eta__day=day))
        events_per_day += list(events["ra"].filter(expiry_date__day=day))
        d = ""
        for event in events_per_day:
            d += format_html("<li> {} </li>", event.get_html_url)

        if day != 0:
            return f"<td><span class='date'>{day}</span><ul> {d} </ul></td>"
        return "<td></td>"

    # formats a week as a tr
    def formatweek(self, theweek, events):
        week = ""
        for d, weekday in theweek:
            week += self.formatday(d, events)
        return f"<tr> {week} </tr>"

    # formats a month as a table
    # filter events by year and month
    def formatmonth(self, withyear=True):
        events = {
            "mtg": AppliedControl.objects.filter(
                eta__year=self.year, eta__month=self.month
            ),
            "ra": RiskAcceptance.objects.filter(
                expiry_date__year=self.year, expiry_date__month=self.month
            ),
        }

        cal = '<table class="calendar">\n'
        cal += f"{self.formatmonthname(self.year, self.month, withyear=withyear).upper()}\n"

        cal += f"{self.formatweekheader()}\n"
        for week in self.monthdays2calendar(self.year, self.month):
            cal += f"{self.formatweek(week, events)}\n"

        return cal
