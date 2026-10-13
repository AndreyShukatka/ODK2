from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.db.models import Sum

from.models import Detail, Operation, Kit, Shift, ProductionRecord
from schedule.models import WorkSchedule, ScheduleEntry

SHIFT_NAMES = {
    'Д': 'День 07:00-15:45',
    'П': 'Вечер 15:45-00:15',
    'У': 'День 07:00-19:00',
    'Н': 'Ночь 19:00-07:00',
    'В': 'Выходной',
    'О': 'Отпуск',
}

def get_shift(user):
    return Shift.objects.get_or_create(user=user, date=timezone.now().date())[0]

@login_required
def dashboard(request):
    shift = get_shift(request.user)
    records = shift.records.select_related('operation__detail','kit','user').order_by('-created_at')
    details = Detail.objects.order_by('-created_at')
    operations = Operation.objects.select_related('detail').order_by('detail__number','number')
    kits = Kit.objects.select_related('detail').prefetch_related('records').order_by('-created_at')[:100]

    # прогресс смены
    closed_records = records.filter(percent__gte=100).count()
    total_records = records.count()
    total_percent = sum(r.percent for r in records)
    progress = int((closed_records / total_records * 100) if total_records else 0)

    today = timezone.localdate()
    schedule = WorkSchedule.objects.filter(month=today.month, year=today.year).order_by('-id').first()
    if not schedule:
        schedule = WorkSchedule.objects.order_by('-year','-month').first()
    my_entry = None; my_shift = None; colleagues = []
    if schedule:
        my_entry = ScheduleEntry.objects.filter(schedule=schedule, employee=request.user, day=today.day).first()
        if my_entry:
            my_shift = my_entry.shift
        if my_shift and my_shift not in ('В','О','', None):
            colleagues = ScheduleEntry.objects.filter(schedule=schedule, day=today.day, shift=my_shift).exclude(employee=request.user).select_related('employee','employee__profile')

    return render(request, 'production/dashboard.html', {
        'shift': shift, 'records': records, 'details': details, 'operations': operations, 'kits': kits,
        'today': today, 'schedule': schedule, 'my_entry': my_entry, 'my_shift': my_shift,
        'my_shift_name': SHIFT_NAMES.get(my_shift, my_shift or '-'),
        'colleagues': colleagues,
        'closed_records': closed_records, 'total_records': total_records,
        'total_percent': total_percent, 'progress': progress,
        'SHIFT_NAMES': SHIFT_NAMES,
    })

@login_required
def journal(request):
    user_id = request.GET.get('user')
    date_str = request.GET.get('date')
    qs = ProductionRecord.objects.select_related('kit__detail','operation','user','shift').order_by('-created_at')
    if user_id:
        qs = qs.filter(user_id=user_id)
    if date_str:
        qs = qs.filter(shift__date=date_str)
    total_time = sum(r.time_min for r in qs)
    total_count = qs.count()
    users = User.objects.filter(productionrecord__isnull=False).distinct().order_by('username')
    dates = Shift.objects.values_list('date', flat=True).distinct().order_by('-date')[:30]

    def format_minutes(total_min):
        total_min = int(round(total_min))
        if total_min <=0: return "0м"
        h = total_min // 60; m = total_min % 60
        if h and m: return f"{h}ч {m}м"
        if h: return f"{h}ч"
        return f"{m}м"

    return render(request, 'production/journal.html', {
        'records': qs[:200],
        'users': users,
        'dates': dates,
        'selected_user': int(user_id) if user_id else None,
        'selected_date': date_str,
        'total_time_display': format_minutes(total_time),
        'total_count': total_count
    })

@login_required
def add_record(request):
    if request.method!='POST':
        return redirect('/')
    op = get_object_or_404(Operation, id=request.POST.get('operation'))
    kit_number = request.POST.get('kit_number','').strip()
    if not kit_number:
        messages.error(request, 'Введи номер комплекта')
        return redirect('/')
    try:
        percent = int(request.POST.get('percent',10))
    except:
        percent = 10

    kit,_=Kit.objects.get_or_create(detail=op.detail, kit_number=kit_number, defaults={'created_by':request.user})
    existing = ProductionRecord.objects.filter(kit=kit, operation=op).first()
    cur = existing.percent if existing else 0
    if cur + percent > 100:
        messages.error(request, f'Оп.{op.number} уже {cur}%, осталось {100-cur}%')
        return redirect('/')
    shift = get_shift(request.user)
    if existing:
        existing.percent = cur + percent
        existing.shift=shift
        existing.save()
    else:
        ProductionRecord.objects.create(kit=kit, operation=op, user=request.user, shift=shift, percent=percent)
    messages.success(request, f'Закрыто {percent}% — {kit.kit_number}')
    return redirect('/')

@login_required
def add_detail(request):
    if request.method=='POST':
        number = request.POST.get('number','').strip()
        name = request.POST.get('name','').strip()
        if number:
            Detail.objects.get_or_create(number=number, defaults={'name': name})
            messages.success(request, f'Деталь {number} создана')
        return redirect('/')
    return render(request, 'production/add_detail.html')

@login_required
def add_operation(request):
    if request.method=='POST':
        detail_id = request.POST.get('detail')
        number = request.POST.get('number','').strip()
        name = request.POST.get('name','').strip()
        try:
            hours = int(request.POST.get('hours') or 0)
            minutes = int(request.POST.get('minutes') or 0)
        except:
            hours, minutes = 0, 0
        total_min = hours * 60 + minutes
        if total_min <= 0:
            messages.error(request, 'Норма должна быть больше 0')
            return redirect('/production/add-operation/')
        if detail_id and number:
            Operation.objects.create(detail_id=detail_id, number=number, name=name, time_norm_min=float(total_min))
            messages.success(request, f'Операция Оп.{number} — норма {hours}ч {minutes}м')
        return redirect('/')
    return render(request, 'production/add_operation.html', {'details': Detail.objects.all()})

@login_required
def kit_detail(request, kit_id):
    return render(request, 'production/kit_detail.html', {'kit': get_object_or_404(Kit, id=kit_id)})

@login_required
def close_shift(request):
    if request.method=='POST':
        s=get_shift(request.user)
        s.is_closed=True
        s.save()
        messages.success(request, 'Смена закрыта')
    return redirect('/')

# ========== API ДЛЯ БЛОКА "+ ЗАКРЫТЬ РАБОТУ" ==========
@login_required
def api_operations(request):
    detail_id = request.GET.get('detail')
    if not detail_id:
        return JsonResponse([], safe=False)
    ops = Operation.objects.filter(detail_id=detail_id).order_by('number')
    data = []
    for o in ops:
        # норма времени
        mins = int(o.time_norm_min or 0)
        h, m = divmod(mins, 60)
        norm = f"{h}ч {m}м" if h else f"{m}м" if m else "1ч 30м"
        data.append({'id': o.id, 'text': f"Оп.{o.number} {o.name} — {norm}"})
    return JsonResponse(data, safe=False)

@login_required
def api_kits(request):
    op_id = request.GET.get('operation')
    if not op_id:
        return JsonResponse({'kits': [], 'used_count': 0})
    op = get_object_or_404(Operation, id=op_id)
    # все комплекты этой детали
    all_kits = Kit.objects.filter(detail=op.detail).values_list('kit_number', flat=True).distinct()
    # уже полностью закрытые по этой операции
    closed = ProductionRecord.objects.filter(operation_id=op_id, percent__gte=100).values_list('kit__kit_number', flat=True)
    free = [k for k in all_kits if k not in list(closed)]
    return JsonResponse({'kits': free[:50], 'used_count': len(closed)})

@login_required
def api_remaining(request):
    op_id = request.GET.get('operation')
    kit_number = request.GET.get('kit_number','').strip()
    if not op_id or not kit_number:
        return JsonResponse({'remaining': 100, 'total': 0})
    total = ProductionRecord.objects.filter(operation_id=op_id, kit__kit_number=kit_number).aggregate(s=Sum('percent'))['s'] or 0
    remaining = max(0, 100 - int(total))
    return JsonResponse({'remaining': remaining, 'total': int(total)})