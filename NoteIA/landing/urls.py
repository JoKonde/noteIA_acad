from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('signup/', views.signup, name='signup'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('success-compte/', views.account_success, name='account_success'),
    # URL pour les cours
    path('cours/', views.list_courses, name='list_courses'),
    path('cours/create/', views.create_course, name='create_course'),
    path('cours/edit/<int:course_id>/', views.edit_course, name='edit_course'),
    path('cours/delete/<int:course_id>/', views.delete_course, name='delete_course'),
    
]
