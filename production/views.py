from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.http import JsonResponse
from .models import Detail, Operation, Kit, Shift, ProductionRecord
from schedule.models import ScheduleEntry, SHIFT_HOURS


def get_today_entry(user, today):
    """Берем запись из твоего графика Бригады №4"""
    entry = ScheduleEntry.objects.filter(
        employee=user,
        schedule__year=today.year,
        schedule__month=today.month,
        day=today.day
    ).select_related('schedule').first()
    return entry


def has_work_today(entry):
    if not entry:
        return False
    # Выходной, пусто, отпуск — не считаем сменой
    if entry.shift in ('', 'В', 'О'):
        return False
    if entry.hours == 0:
        # на всякий случай берем из SHIFT_HOURS
        return SHIFT_HOURS.get(entry.shift, 0) > 0
    return True


@login_required
def dashboard(request):
    today = timezone.now().date()
    entry = get_today_entry(request.user, today)

    if not has_work_today(entry):
        return render(request, 'production/dashboard.html', {
            'has_shift': False,
            'today': today,
            'hourly_rate': request.user.profile.hourly_rate,
            'pay_type': request.user.profile.pay_type,
            'entry': entry,
        })

    # Есть смена в графике
    hours = entry.hours if entry.hours else SHIFT_HOURS.get(entry.shift, 11.2)
    shift, _ = Shift.objects.get_or_create(
        user=request.user,
        date=today,
        defaults={'scheduled_hours': hours}
    )
    if shift.scheduled_hours != hours:
        shift.scheduled_hours = hours
        shift.save()

    shift.recalc()
    records = shift.records.select_related('kit__detail', 'operation').all()

    return render(request, 'production/dashboard.html', {
        'has_shift': True,
        'shift': shift,
        'entry': entry,
        'today': today,
        'details': Detail.objects.all(),
        'operations': Operation.objects.select_related('detail').all(),
        'kits': Kit.objects.select_related('detail').prefetch_related('records').all(),
        'records': records,
        'total_earnings': shift.total_earnings,
        'total_time_min': shift.total_time_min,
        'pay_type': request.user.profile.pay_type,
        'hourly_rate': request.user.profile.hourly_rate,
        'closed_records': records.count(),
        'total_records': 20,
        'progress': min(100, records.count() * 5),
        'my_shift': entry.shift,
        'colleagues': [],
    })


@login_required
def add_record(request):
    if request.method != 'POST':
        return redirect('/')
    op_id = request.POST.get('operation')
    kit_number = request.POST.get('kit_number', '').strip()
    try:
        percent = int(request.POST.get('percent', 0))
    except:
        percent = 0
    if not op_id or not kit_number or percent <= 0:
        messages.error(request, 'Заполни поля');
        return redirect('/')

    today = timezone.now().date()
    entry = get_today_entry(request.user, today)
    if not has_work_today(entry):
        messages.error(request, 'Сегодня нет смены в графике — закрой смену нельзя');
        return redirect('/')

    operation = get_object_or_404(Operation, id=op_id)
    hours = entry.hours if entry.hours else SHIFT_HOURS.get(entry.shift, 11.2)
    shift, _ = Shift.objects.get_or_create(user=request.user, date=today, defaults={'scheduled_hours': hours})

    kit, _ = Kit.objects.get_or_create(
        detail=operation.detail,
        kit_number=kit_number,
        defaults={'created_by': request.user}
    )
    existing = ProductionRecord.objects.filter(kit=kit, operation=operation).first()
    already = existing.percent if existing else 0
    if percent > 100 - already:
        messages.error(request, f'Можно только {100 - already}%');
        return redirect('/')
    record, _ = ProductionRecord.objects.update_or_create(
        kit=kit, operation=operation,
        defaults={'user': request.user, 'shift': shift, 'percent': already + percent}
    )
    record.save()
    return redirect('/')


@login_required
def add_detail(request):
    if request.method == 'POST':
        number = request.POST.get('number', '').strip();
        name = request.POST.get('name', '').strip()
        if number and name: Detail.objects.get_or_create(number=number, defaults={'name': name})
        return redirect('/')
    return render(request, 'production/add_detail.html')


@login_required
def add_operation(request):
    if request.method == 'POST':
        try:
            detail = Detail.objects.get(id=request.POST.get('detail'))
            Operation.objects.create(detail=detail, number=int(request.POST.get('number')),
                                     name=request.POST.get('name', '').strip(),
                                     time_norm_min=float(request.POST.get('time_norm_min')))
        except Exception as e:
            messages.error(request, f'Ошибка:{e}')
        return redirect('/')
    return render(request, 'production/add_operation.html', {'details': Detail.objects.all()})


@login_required
def kit_detail(request, kit_id):
    kit = get_object_or_404(Kit, id=kit_id)
    return render(request, 'production/kit_detail.html', {'kit': kit})


@login_required
def close_shift(request):
    today = timezone.now().date()
    shift = Shift.objects.filter(user=request.user, date=today).first()
    if shift: shift.is_closed = True; shift.save()
    return redirect('journal')


@login_required
def journal(request):
    shifts = Shift.objects.filter(user=request.user).order_by('-date')
    records = ProductionRecord.objects.filter(user=request.user).select_related('kit__detail', 'operation',
                                                                                'shift').order_by('-created_at')[:300]
    return render(request, 'production/journal.html', {'shifts': shifts, 'records': records})


@login_required
def api_operations(request):
    detail_id = request.GET.get('detail_id')
    if not detail_id: return JsonResponse([], safe=False)
    ops = Operation.objects.filter(detail_id=detail_id).values('id', 'number', 'name', 'time_norm_min')
    return JsonResponse(
        [{'id': o['id'], 'number': o['number'], 'name': o['name'], 'norm': o['time_norm_min']} for o in ops],
        safe=False)


@login_required
def api_kits(request):
    detail_id = request.GET.get('detail_id');
    op_id = request.GET.get('operation_id')
    if not detail_id or not op_id: return JsonResponse([], safe=False)
    result = []
    for k in Kit.objects.filter(detail_id=detail_id):
        rec = ProductionRecord.objects.filter(kit=k, operation_id=op_id).first()
        cur = rec.percent if rec else 0
        if cur >= 100: continue
        result.append({'number': k.kit_number, 'closed': cur, 'remaining': 100 - cur})
    return JsonResponse(result, safe=False)


@login_required
def api_remaining(request):
    kit_number = request.GET.get('kit_number', '').strip();
    op_id = request.GET.get('operation_id');
    detail_id = request.GET.get('detail_id')
    if not kit_number or not op_id or not detail_id: return JsonResponse({'remaining': 100})
    kit = Kit.objects.filter(detail_id=detail_id, kit_number=kit_number).first()
    if not kit: return JsonResponse({'remaining': 100})
    rec = ProductionRecord.objects.filter(kit=kit, operation_id=op_id).first()
    cur = rec.percent if rec else 0
    return JsonResponse({'closed': cur, 'remaining': 100 - cur})