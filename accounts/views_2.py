from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Profile, AccessGrant

def register_view(request):
    if request.method=='POST':
        username = request.POST.get('username','').strip()
        password = request.POST.get('password','')
        last_name = request.POST.get('last_name','').strip()
        first_name = request.POST.get('first_name','').strip()
        middle_name = request.POST.get('middle_name','').strip()
        if not last_name or not first_name or not middle_name:
            return render(request,'accounts/register.html', {'error': 'Фамилия, Имя и Отчество обязательны!','data': request.POST})
        if User.objects.filter(username=username).exists():
            return render(request,'accounts/register.html', {'error':'Такой логин уже есть','data':request.POST})
        u=User.objects.create_user(username=username,password=password,last_name=last_name,first_name=first_name)
        profile, _ = Profile.objects.get_or_create(user=u)
        profile.role = request.POST.get('role','cnc_operator')
        profile.pay_type = request.POST.get('pay_type','piecework')
        try: profile.hourly_rate = float(request.POST.get('hourly_rate',400) or 400)
        except: profile.hourly_rate = 400
        profile.middle_name = middle_name
        profile.save()
        login(request,u)
        return redirect('/')
    return render(request,'accounts/register.html')

@login_required
def profile_view(request):
    return render(request,'accounts/profile.html',{'given':AccessGrant.objects.filter(granter=request.user),'received':AccessGrant.objects.filter(grantee=request.user),'users':User.objects.exclude(id=request.user.id)})

@login_required
def grant_access(request):
    if request.method=='POST':
        t=get_object_or_404(User, id=request.POST['grantee'])
        AccessGrant.objects.get_or_create(granter=request.user, grantee=t)
    return redirect('profile')

@login_required
def revoke_access(request,pk):
    AccessGrant.objects.filter(id=pk, granter=request.user).delete()
    return redirect('profile')

@login_required
def settings_rate(request):
    profile = request.user.profile
    if request.method == 'POST':
        try:
            rate = float(request.POST.get('hourly_rate'))
            middle = request.POST.get('middle_name','').strip()
            last = request.POST.get('last_name','').strip()
            first = request.POST.get('first_name','').strip()
            pay_type = request.POST.get('pay_type')
            if rate < 50 or rate > 10000: raise ValueError('Ставка должна быть 50-10000')
            profile.hourly_rate = rate
            if middle: profile.middle_name = middle
            if pay_type in ('hourly','piecework'): profile.pay_type = pay_type
            profile.save()
            if last: request.user.last_name = last
            if first: request.user.first_name = first
            request.user.save()
            messages.success(request, f'Сохранено: ставка {rate:.0f} ₽/ч, {profile.short_name}')
        except Exception as e:
            messages.error(request, f'Ошибка: {e}')
        return redirect('settings_rate')
    return render(request, 'accounts/settings.html', {'profile': profile})
