from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('stocks/', views.stocks, name='stocks'),
    path('operations/<int:pk>/pdf/', views.operation_pdf, name='operation_pdf'),
    path('operations/<int:pk>/invoice/generate/', views.operation_invoice_generate, name='operation_invoice_generate'),
]