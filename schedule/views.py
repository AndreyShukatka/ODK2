import calendar
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from.models import WorkSchedule, ScheduleEntry

@login_required
def schedule_list(request):
    schedules = WorkSchedule.objects.all().order_by('-year','-month')
    return render(request, 'schedule/list.html', {'schedules': schedules})

@login_required
def schedule_create(request):
    if request.method == 'POST':
        brigade_no = request.POST.get('brigade_no') or 4
        month = int(request.POST.get('month') or 10)
        year = int(request.POST.get('year') or 2026)
        norm_hours = request.POST.get('norm_hours') or 176
        sched = WorkSchedule.objects.create(brigade_no=brigade_no, month=month, year=year, norm_hours=norm_hours)
        emp_ids = request.POST.getlist('employees')
        days = calendar.monthrange(year, month)[1]
        bulk = []
        for emp_id in emp_ids:
            for d in range(1, days+1):
                bulk.append(ScheduleEntry(schedule=sched, employee_id=emp_id, day=d, shift='', hours=0))
        ScheduleEntry.objects.bulk_create(bulk)
        return redirect('schedule_edit', pk=sched.id)
    employees = User.objects.all().order_by('last_name','first_name')
    return render(request, 'schedule/form.html', {'employees': employees})

@login_required
def schedule_edit(request, pk):
    sched = get_object_or_404(WorkSchedule, pk=pk)
    days = list(range(1, calendar.monthrange(sched.year, sched.month)[1]+1))
    employees = User.objects.filter(scheduleentry__schedule=sched).distinct().order_by('last_name','first_name')
    if request.method == 'POST':
        for emp in employees:
            for d in days:
                shift = request.POST.get(f'shift_{emp.id}_{d}','').strip().upper()
                hours_raw = request.POST.get(f'hours_{emp.id}_{d}','0').replace(',','.')
                try:
                    hours = float(hours_raw) if hours_raw else 0
                except:
                    hours = 0
                if hours==0 and shift in ('Д','П','У','Н'):
                    hours = {'Д':8,'П':8,'У':11.2,'Н':11.2}.get(shift,0)
                obj, _ = ScheduleEntry.objects.get_or_create(schedule=sched, employee=emp, day=d)
                obj.shift = shift
                obj.hours = hours
                obj.save()
        return redirect('schedule_edit', pk=sched.id)

    entries = ScheduleEntry.objects.filter(schedule=sched)
    matrix = {}
    totals = {}
    for e in entries:
        matrix.setdefault(e.employee_id, {})[e.day] = e
    norm = float(sched.norm_hours or 176)
    for emp in employees:
        total = sum([float(x.hours or 0) for x in entries.filter(employee=emp) if x.shift not in ('В','О','')])
        ur = min(total, norm)
        sv = max(0, total - norm)
        totals[emp.id] = {
            'ur': f"{ur:.1f}".replace('.',','),
            'sv': f"{sv:.1f}".replace('.',',') if sv else "0"
        }
    return render(request, 'schedule/edit.html', {'schedule': sched, 'employees': employees, 'days': days, 'matrix': matrix, 'totals': totals})

@login_required
def schedule_excel(request, pk):
    from django.http import HttpResponse
    return HttpResponse("excel заглушка")