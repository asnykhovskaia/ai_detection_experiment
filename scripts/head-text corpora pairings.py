import os
import shutil

total_folder = r"/Users/arinasnykhovskaya/Downloads/rltc"
folder_x = r"/Users/arinasnykhovskaya/Downloads/rltc/essays_heads"
folder_y = r"/Users/arinasnykhovskaya/Downloads/rltc/essays"

os.makedirs(folder_y, exist_ok=True)

head_numbers = set()
for file in os.listdir(folder_x):
    if ".head." in file:
        number = file.split(".head.")[0]
        head_numbers.add(number)

for file in os.listdir(total_folder):
    full_path = os.path.join(total_folder, file)
    
    if os.path.isfile(full_path):
        name_without_ext, _ = os.path.splitext(file)
        
        if name_without_ext in head_numbers:
            destination_path = os.path.join(folder_y, file)
            shutil.move(full_path, destination_path)
