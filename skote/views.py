from django.http import request
from django.shortcuts import redirect, render
from django.views import View   
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.base import TemplateView
from allauth.account.views import PasswordSetView,PasswordChangeView
from django.urls import reverse_lazy

# utillity
class DashboardView(LoginRequiredMixin,View):
    def get(self, request):
        greeting = {}
        greeting['heading'] = "Dashboard"
        greeting['pageview'] = "Dashboards"        
        return render(request, 'dashboard/dashboard.html',greeting)




# Authentication
class PagesLoginView(View):
    def get(self, request):
        return render(request, 'authentication/pages-login.html')
class PagesRegisterView(View):
    def get(self, request):
        return render(request, 'authentication/pages-register.html')
class PagesRecoverpwView(View):
    def get(self, request):
        return render(request, 'authentication/pages-recoverpw.html')
class PagesLockscreenView(View):
    def get(self, request):
        return render(request, 'authentication/pages-lockscreen.html')

class PagesConfirmmailView(View):
    def get(self, request):
        return render(request, 'authentication/pages-confirmmail.html')

class PagesEmailVerificationView(View):
    def get(self, request):
        return render(request, 'authentication/pages-emailverificationmail.html')

class PagesTwoStepVerificationView(View):
    def get(self, request):
        return render(request, 'authentication/pages-twostepverificationmail.html')
class PagesLogin2View(View):
    def get(self, request):
        return render(request, 'authentication/pages-login-2.html')
class PagesRegister2View(View):
    def get(self, request):
        return render(request, 'authentication/pages-register-2.html')
class PagesRecoverpw2View(View):
    def get(self, request):
        return render(request, 'authentication/pages-recoverpw2.html')
class PagesLockscreen2View(View):
    def get(self, request):
        return render(request, 'authentication/pages-lockscreen2.html')

class PagesConfirmmail2View(View):
    def get(self, request):
        return render(request, 'authentication/pages-confirmmail-2.html')

class PagesEmailVerification2View(View):
    def get(self, request):
        return render(request, 'authentication/pages-emailverificationmail-2.html')

class PagesTwoStepVerification2View(View):
    def get(self, request):
        return render(request, 'authentication/pages-twostepverificationmail-2.html')

class MyPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    success_url = reverse_lazy('dashboard')
class MyPasswordSetView(LoginRequiredMixin, PasswordSetView):
    success_url = reverse_lazy('dashboard')