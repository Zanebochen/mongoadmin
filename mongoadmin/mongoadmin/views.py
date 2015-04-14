# -*- coding: utf-8 -*-
from django.contrib import auth
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.shortcuts import render
from django.views.decorators.http import require_GET
from mongoadmin.forms import LoginForm


def login(request, type_id):
    error = []
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            username = data['username']
            password = data['password']
            user = auth.authenticate(username=username, password=password)
            if user:
                auth.login(request, user)
                redirect_url = request.GET.get(REDIRECT_FIELD_NAME, '') or reverse('index')
                return HttpResponseRedirect(redirect_url)
            else:
                error.append(u'请输入正确的密码.')
        else:
            error.append("用户名或密码错误.")
    elif request.user.is_authenticated():
        return HttpResponseRedirect(reverse('index'))
    return render(request, 'login.html', {'error': error, 'type_id': type_id})


@require_GET
def logout(request):
    if request.user.is_authenticated():
        auth.logout(request)
    return HttpResponseRedirect(reverse("home"))

