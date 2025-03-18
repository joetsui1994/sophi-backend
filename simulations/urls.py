from django.urls import path, include
from rest_framework import routers
from . import views

router = routers.DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
    path('simulation-repository/', views.SimulationRepository.as_view()),
    path('get-simulation-data/<slug:uuid>/', views.get_simulation_data),
    path('get-inference-tree/<slug:uuid>/', views.get_inference_tree),
    path('get-migratory-event-counts/<slug:uuid>/', views.get_migratory_event_counts),
    path('get-earliest-introductions/<slug:uuid>/', views.get_earliest_introductions),
]