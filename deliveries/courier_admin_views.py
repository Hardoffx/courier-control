from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from accounts.models import User
from .models import Route


def dispatcher_required(view):
    @login_required
    def wrapped(request,*args,**kwargs):
        if not request.user.is_dispatcher: raise PermissionDenied
        return view(request,*args,**kwargs)
    return wrapped


def _courier_users():
    return User.objects.filter(role=User.Role.COURIER, is_superuser=False)


@dispatcher_required
def courier_list(request):
    couriers=_courier_users().annotate(route_count=Count('default_routes',filter=Q(default_routes__is_active=True))).order_by('-is_active','-is_reserve_courier','first_name','username')
    return render(request,'dispatcher/couriers/list.html',{'couriers':couriers})


@dispatcher_required
def courier_edit(request,pk=None):
    courier=get_object_or_404(_courier_users(),pk=pk) if pk else None
    if request.method=='POST':
        username=request.POST.get('username','').strip()
        first_name=request.POST.get('first_name','').strip()[:150]
        last_name=request.POST.get('last_name','').strip()[:150]
        phone=request.POST.get('phone','').strip()[:32]
        password=request.POST.get('password','')
        if not username:
            messages.error(request,'Укажите логин')
        elif User.objects.filter(username__iexact=username).exclude(pk=courier.pk if courier else None).exists():
            messages.error(request,'Такой логин уже используется')
        elif not courier and not password:
            messages.error(request,'Для нового курьера задайте временный пароль')
        else:
            courier=courier or User(role=User.Role.COURIER)
            courier.username=username; courier.first_name=first_name; courier.last_name=last_name; courier.phone=phone
            courier.is_reserve_courier=request.POST.get('is_reserve_courier')=='on'
            courier.is_active=request.POST.get('is_active')=='on'
            if password: courier.set_password(password)
            elif not courier.pk: courier.set_unusable_password()
            courier.save()
            messages.success(request,'Курьер сохранён')
            return redirect('courier_manage_list')
    return render(request,'dispatcher/couriers/form.html',{'courier':courier})


@dispatcher_required
@require_POST
def courier_toggle(request,pk):
    courier=get_object_or_404(_courier_users(),pk=pk)
    courier.is_active=not courier.is_active; courier.save(update_fields=['is_active'])
    messages.success(request,'Курьер активирован' if courier.is_active else 'Курьер отключён. История маршрутов сохранена.')
    return redirect('courier_manage_list')
