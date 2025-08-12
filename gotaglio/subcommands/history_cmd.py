import time

from ..constants import app_configuration
from ..shared import get_files_sorted_by_creation

def show_history():
  records = get_files_sorted_by_creation(app_configuration["log_folder"])
  for r in records:
      local_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(r[1]))
      print(f"{r[0]}: {local_time}")
