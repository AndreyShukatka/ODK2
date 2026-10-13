from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

def format_minutes(total_min):
    """100.2 -> 1ч 40м, 30 -> 30м, 120 -> 2ч"""
    try:
        total_min = float(total_min)
    except:
        return "0м"
    total_min = int(round(total_min))
    if total_min <= 0:
        return "0м"
    h = total_min // 60
    m = total_min % 60
    if h > 0 and m > 0:
        return f"{h}ч {m}м"
    if h > 0:
        return f"{h}ч"
    return f"{m}м"

class Detail(models.Model):
    number = models.CharField(max_length=100, unique=True, verbose_name="Номер детали")
    name = models.CharField(max_length=255, verbose_name="Название")
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"{self.number} — {self.name}"

class Operation(models.Model):
    detail = models.ForeignKey(Detail, on_delete=models.CASCADE, related_name='operations')
    number = models.IntegerField(verbose_name="№ операции")
    name = models.CharField(max_length=255, verbose_name="Название операции")
    time_norm_min = models.FloatField(verbose_name="Норма на 100% (мин)")
    class Meta:
        unique_together = ('detail','number')
        ordering = ['number']
    def __str__(self): return f"{self.detail.number} Оп.{self.number}"
    @property
    def norm_display(self):
        return format_minutes(self.time_norm_min)

class Kit(models.Model):
    detail = models.ForeignKey(Detail, on_delete=models.CASCADE, related_name='kits')
    kit_number = models.CharField(max_length=100, verbose_name="Номер комплекта")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    is_fully_closed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('detail','kit_number')
        ordering = ['-created_at']
    def operation_percent(self, op):
        rec = self.records.filter(operation=op).first()
        return rec.percent if rec else 0
    def total_percent(self):
        ops = self.detail.operations.count()
        if not ops: return 0
        total = sum(self.operation_percent(o) for o in self.detail.operations.all())
        return int(total / ops)
    def check_fully_closed(self):
        if not self.detail.operations.exists(): return False
        return all(self.operation_percent(op) >= 100 for op in self.detail.operations.all())

class Shift(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    total_details = models.IntegerField(default=0)
    total_time_min = models.FloatField(default=0)
    is_closed = models.BooleanField(default=False)
    class Meta:
        unique_together = ('user','date')
        ordering = ['-date']
    def recalc(self):
        recs = self.records.all()
        self.total_details = recs.count()
        self.total_time_min = round(sum(r.time_min for r in recs),2)
        self.save()
    @property
    def total_time_display(self):
        return format_minutes(self.total_time_min)

class ProductionRecord(models.Model):
    kit = models.ForeignKey(Kit, on_delete=models.CASCADE, related_name='records')
    operation = models.ForeignKey(Operation, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE, related_name='records', null=True, blank=True)
    percent = models.IntegerField()
    time_min = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = ('kit','operation')
        ordering = ['-created_at']
    @property
    def remaining(self): return 100 - self.percent
    @property
    def time_display(self):
        return format_minutes(self.time_min)
    def save(self, *args, **kwargs):
        self.time_min = round(self.operation.time_norm_min * self.percent / 100.0, 2)
        super().save(*args, **kwargs)
        self.kit.is_fully_closed = self.kit.check_fully_closed()
        self.kit.save()
        if self.shift: self.shift.recalc()