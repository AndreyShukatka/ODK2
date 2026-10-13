from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from.models import Profile, AccessGrant

def register_view(request):
    if request.method=='POST':
        username = request.POST.get('username','').strip()
        password = request.POST.get('password','')
        last_name = request.POST.get('last_name','').strip()
        first_name = request.POST.get('first_name','').strip()
        middle_name = request.POST.get('middle_name','').strip()

        if not last_name or not first_name or not middle_name:
            return render(request,'accounts/register.html', {
                'error': 'Фамилия, Имя и Отчество обязательны!',
                'data': request.POST
            })

        if User.objects.filter(username=username).exists():
            return render(request,'accounts/register.html', {'error':'Такой логин уже есть','data':request.POST})

        u=User.objects.create_user(
            username=username,
            password=password,
            last_name=last_name,
            first_name=first_name
        )
        Profile.objects.create(
            user=u,
            role=request.POST.get('role','cnc_operator'),
            pay_type=request.POST.get('pay_type','piecework'),
            hourly_rate=request.POST.get('hourly_rate',400) or 400,
            middle_name=middle_name
        )
        login(request,u)
        return redirect('/')
    return render(request,'accounts/register.html')

@login_required
def profile_view(request):
    return render(request,'accounts/profile.html',{
        'given':AccessGrant.objects.filter(granter=request.user),
        'received':AccessGrant.objects.filter(grantee=request.user),
        'users':User.objects.exclude(id=request.user.id)
    })

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