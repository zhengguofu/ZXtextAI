from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.pytools_health, name="pytools-health"),
    path("captcha/analyze/", views.captcha_analyze, name="pytools-captcha-analyze"),
    path("captcha/ocr/", views.captcha_ocr, name="pytools-captcha-ocr"),
    path("captcha/slider-distance/", views.captcha_slider_distance, name="pytools-captcha-slider-distance"),
]
