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

    # URL pour les notes texte

    path('notes/select-course/', views.select_course_for_note, name='select_course_for_note'),
    path('notes/<int:course_id>/list/', views.list_notes, name='list_notes'),
    path('notes/<int:course_id>/create/', views.create_note, name='create_note'),
    path('note/<int:note_id>/', views.note_detail, name='note_detail'),
    path('note/<int:note_id>/create-text/', views.create_textnote, name='create_textnote'),
    path('note/<int:note_id>/invite/', views.invite_collaborators, name='invite_collaborators'),

    path('note/<int:note_id>/edit/', views.edit_note, name='edit_note'),
    path('note/<int:note_id>/delete/', views.delete_note, name='delete_note'),
    
    path('note/<int:note_id>/create-image/', views.create_imagenote, name='create_imagenote'),
    path('image/<int:image_id>/delete/', views.delete_imagenote, name='delete_imagenote'),
    
    path('note/<int:note_id>/create-pdf/', views.create_pdfnote, name='create_pdfnote'),
    path('pdf/<int:pdf_id>/delete/', views.delete_pdfnote, name='delete_pdfnote'),
    
    # URLs pour les résumés
    path('note/<int:note_id>/generate-resume/', views.generate_resume, name='generate_resume'),
    path('note/<int:note_id>/resumes/', views.view_resumes, name='view_resumes'),
    path('resume/<int:resume_id>/delete/', views.delete_resume, name='delete_resume'),
]
