import shutil
import datetime
import os

# Копируем базу данных с датой
source = 'coffee_training.db'
backup_dir = 'backups'
os.makedirs(backup_dir, exist_ok=True)

date_str = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')
backup_file = f'{backup_dir}/backup_{date_str}.db'

shutil.copy2(source, backup_file)
print(f"✅ Резервная копия создана: {backup_file}")