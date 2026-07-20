"""skote URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from .views import MyPasswordSetView ,MyPasswordChangeView
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from studio import views as studio_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # BCP Studio — Control Room is the home page.
    # Bare 'dashboard' name kept for Skote's shipped auth templates.
    path('', studio_views.dashboard, name='dashboard'),
    path('', include('studio.urls')),

    # Skote demo layouts/pages (kept so their url names still resolve)
    path('layout/',include('layout.urls')),
   
    #Authencation
    # path('authentication/',include('authentication.urls')),
    #Pages
    path('pages/',include('pages.urls')),

    # Allauth
    path('account/', include('allauth.urls')),
    path('auth-logout/',TemplateView.as_view(template_name="account/logout-success.html"),name ='pages-logout'),
    path('auth-lockscreen/',TemplateView.as_view(template_name="account/lock-screen.html"),name ='pages-lockscreen'),
        #Custum change password done page redirect
    path('accounts/password/change/', login_required(MyPasswordChangeView.as_view()), name="account_change_password"),
    #Custum set password done page redirect
    path('accounts/password/set/', login_required(MyPasswordSetView.as_view()), name="account_set_password"),
]

