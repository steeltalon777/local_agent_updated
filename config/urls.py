from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect

def redirect_to_home(request):
    return redirect('/')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(
        template_name='main/login.html',
        redirect_authenticated_user=True,  # Если уже залогинен - на главную
        next_page='/'  # После логина - на главную
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(
        template_name='main/logged_out.html',
        next_page='/login/'
    ), name='logout'),
    path('', include('main.urls')),
]