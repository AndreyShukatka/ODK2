from django.db import models
from django.contrib.auth.models import User

SHIFT_CHOICES = [
    ('', '—'),
    ('Д', 'Д — 07:00-15:45 (8ч)'),
    ('П', 'П — 15:45-00:15 (8ч)'),
    ('У', 'У — 07:00-19:00 (11,2ч)'),
    ('Н', 'Н — 19:00-07:00 (11,2ч)'),
    ('В', 'В — выходной'),
    ('О', 'О — отпуск'),
]

SHIFT_HOURS = {
    'Д': 8.0,
    'П': 8.0,
    'У': 11.2,
    'Н': 11.2,
    'В': 0,
    'О': 0,
    '': 0,
}

class WorkSchedule(models.Model):
    brigade_no = models.CharField(max_length=10, default="4", verbose_name="Бригада №")
    year = models.IntegerField(default=2026)
    month = models.IntegerField(default=10)
    norm_hours = models.FloatField(default=176.0, verbose_name="Норма Ур.")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Бригада №{self.brigade_no} {self.month:02d}/{self.year}"

class ScheduleEntry(models.Model):
    schedule = models.ForeignKey(WorkSchedule, on_delete=models.CASCADE, related_name="entries")
    employee = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Сотрудник")
    day = models.IntegerField()
    shift = models.CharField(max_length=2, choices=SHIFT_CHOICES, blank=True, default="")
    hours = models.FloatField(default=0)

    class Meta:
        unique_together = ('schedule','employee','day')
        ordering = ['employee__username','day']
