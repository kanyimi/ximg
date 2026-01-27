from django.urls import path
from . import views

app_name = "photohostapp"

urlpatterns = [
    path("", views.create_section_and_upload, name="create"),
    path("s/<slug:slug>/", views.section_detail, name="section_detail"),
    path("s/<slug:slug>/download.zip", views.download_zip, name="download_zip"),
  #  path('upload_image/', views.upload_image_view, name='upload_image'),
  #   path( "file/<int:file_id>/download/", views.download_file,name="download_file"),
    path("<slug:slug>/file/<int:file_id>/download/", views.download_file, name="download_file"),


]
