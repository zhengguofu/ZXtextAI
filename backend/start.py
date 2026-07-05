import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

try:
    from uvicorn import run
    import django
    django.setup()
except ImportError as exc:
    print(f"Error: {exc}")
    print("Make sure Django and uvicorn are installed in your Python environment")
    sys.exit(1)

if __name__ == '__main__':
    run(
        "backend.asgi:application",
        host="127.0.0.1",
        port=8000,
        log_level="info",
        reload=False
    )
