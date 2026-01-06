from django.urls import path
from . import views

app_name = "secret_notes"

urlpatterns = [
    path("", views.create, name="create"),
    path("created/<uuid:note_id>/", views.created, name="created"),
    path("note/<uuid:note_id>/", views.view_note, name="view"),
]
