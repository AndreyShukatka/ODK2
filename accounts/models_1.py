from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

DEFAULT_FIO = "Отсутствует"

class Profile(models.Model):
    ROLE=[('employee','Сотрудник'),('operator','Оператор'),('cnc_operator','Оператор ЧПУ'),('cnc_adjuster','Наладчик ЧПУ')]
    PAY=[('hourly','Повременщик'),('piecework','Сдельщик')]
    user=models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role=models.CharField(max_length=20, choices=ROLE, default='cnc_operator')
    pay_type=models.CharField(max_length=20, choices=PAY, default='piecework')
    hourly_rate=models.DecimalField(max_digits=10, decimal_places=2, default=400)
    middle_name=models.CharField(max_length=100, default=DEFAULT_FIO, verbose_name="Отчество")
    @property
    def safe_last(self): return self.user.last_name.strip() or DEFAULT_FIO
    @property
    def safe_first(self): return self.user.first_name.strip() or DEFAULT_FIO
    @property
    def safe_middle(self): return (self.middle_name or "").strip() or DEFAULT_FIO
    @property
    def full_name(self): return f"{self.safe_last} {self.safe_first} {self.safe_middle}"
    @property
    def short_name(self):
        last=self.safe_last
        f=f"{self.safe_first[0]}." if self.safe_first!=DEFAULT_FIO and self.safe_first else "О."
        m=f"{self.safe_middle[0]}." if self.safe_middle!=DEFAULT_FIO and self.safe_middle else "О."
        if last==DEFAULT_FIO and self.safe_first==DEFAULT_FIO and self.safe_middle==DEFAULT_FIO: return "Отсутствует О.О."
        return f"{last} {f}{m}".strip()
    def save(self,*args,**kwargs):
        if not self.middle_name: self.middle_name=DEFAULT_FIO
        if not self.user.last_name: self.user.last_name=DEFAULT_FIO
        if not self.user.first_name: self.user.first_name=DEFAULT_FIO; self.user.save()
        super().save(*args,**kwargs)
    def __str__(self): return self.full_name

class AccessGrant(models.Model):
    granter=models.ForeignKey(User, on_delete=models.CASCADE, related_name='granted')
    grantee=models.ForeignKey(User, on_delete=models.CASCADE, related_name='received')
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: unique_together=('granter','grantee')

@receiver(post_save, sender=User)
def create_or_fix_profile(sender, instance, created, **kwargs):
    profile,_=Profile.objects.get_or_create(user=instance, defaults={'middle_name': DEFAULT_FIO})
    changed=False
    if not instance.last_name: instance.last_name=DEFAULT_FIO; changed=True
    if not instance.first_name: instance.first_name=DEFAULT_FIO; changed=True
    if changed: instance.save()
    if not profile.middle_name: profile.middle_name=DEFAULT_FIO; profile.save()
