from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('stocks/', views.stocks, name='stocks'),
    path('operations/', views.operations_list, name='operations_list'),
    path('operations/<int:pk>/pdf/', views.operation_pdf, name='operation_pdf'),
    path('operations/<int:pk>/invoice/generate/', views.operation_invoice_generate, name='operation_invoice_generate'),
    path('catalog/items/', views.items_list, name='items_list'),
    path('catalog/items/create/', views.item_create, name='item_create'),
    path('catalog/items/<int:pk>/edit/', views.item_edit, name='item_edit'),
    path('catalog/categories/', views.categories_list, name='categories_list'),
    path('catalog/categories/create/', views.category_create, name='category_create'),
    path('catalog/categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('sites/', views.sites_list, name='sites_list'),
    path('sites/create/', views.site_create, name='site_create'),
    path('sites/<int:pk>/edit/', views.site_edit, name='site_edit'),
]
