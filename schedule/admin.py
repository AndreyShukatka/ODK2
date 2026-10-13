from django.contrib import admin
from.models import WorkSchedule, ScheduleEntry

class ScheduleEntryInline(admin.TabularInline):
    model = ScheduleEntry
    extra = 0
    autocomplete_fields = ['employee']
    fields = ('employee','day','shift','hours')
    ordering = ('employee','day')

@admin.register(WorkSchedule)
class WorkScheduleAdmin(admin.ModelAdmin):
    list_display = ('id','brigade_no','month','year','norm_hours')
    list_filter = ('year','month','brigade_no')
    inlines = [ScheduleEntryInline]
    search_fields = ('brigade_no',)

@admin.register(ScheduleEntry)
class ScheduleEntryAdmin(admin.ModelAdmin):
    list_display = ('schedule','employee','day','shift','hours')
    list_filter = ('schedule__year','schedule__month','shift','day')
    search_fields = ('employee__username','employee__last_name')
    autocomplete_fields = ['employee','schedule']
    list_editable = ('shift','hours')