from django.contrib import admin
from .models import Detail, Operation, Kit, Shift, ProductionRecord
admin.site.register(Detail)
admin.site.register(Operation)
admin.site.register(Kit)
admin.site.register(Shift)
admin.site.register(ProductionRecord)
