from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart_view, name='cart_view'),
    path('checkout/', views.checkout, name='checkout'),

        # Auth routes
    path('login/', views.user_login, name='user_login'),
    path('admin-login/', views.admin_login, name='admin_login'),
    path('logout/', views.user_logout, name='logout'),

    # Admin dashboard & home
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
     path('myadmin/products/', views.admin_products, name='admin_products'),
    path('myadmin/products/add/', views.admin_add_product, name='admin_add_product'),
    path('myadmin/products/<int:product_id>/edit/', views.admin_edit_product, name='admin_edit_product'),
    path('myadmin/products/<int:product_id>/delete/', views.admin_delete_product, name='admin_delete_product'),

    path('myadmin/categories/', views.admin_categories, name='admin_categories'),
    path('myadmin/categories/add/', views.admin_add_category, name='admin_add_category'),
    path('myadmin/categories/<int:category_id>/edit/', views.admin_edit_category, name='admin_edit_category'),
    path('myadmin/categories/<int:category_id>/delete/', views.admin_delete_category, name='admin_delete_category'),

    path('myadmin/orders/', views.admin_orders, name='admin_orders'),

    # path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('add-to-cart/<int:pk>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_view, name='cart'),
    path('update-cart/<int:product_id>/', views.update_cart_quantity, name='update_cart_quantity'),
    path('update-cart/', views.update_cart, name='update_cart'),
]
