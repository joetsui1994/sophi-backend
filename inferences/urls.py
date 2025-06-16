from django.urls import path, include
from rest_framework import routers
from .views import InferenceSubmission
from . import views

router = routers.DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
    path('submit-inference/<slug:simulation_uuid>/', InferenceSubmission.as_view()),
    path('get-inference-data/<slug:inference_uuid>/', views.get_inference_data),
    path('delete-inference/<slug:inference_uuid>/', views.delete_inference),
]