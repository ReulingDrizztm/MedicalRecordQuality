#!/usr/bin/env python
import os
import sys
curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.join(os.path.split(curPath)[0], 'MedicalQuality')
sys.path.append(rootPath)

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MedicalRecordQuality.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)
