#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    # `DJANGO_SETTINGS_MODULE` has been before here. So we need to cover it.
    # Maybe it is set by Eclipse.
    os.environ['DJANGO_SETTINGS_MODULE'] = "mongoadmin.settings.dev"
#     os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mongoadmin.settings.dev")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
