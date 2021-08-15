#!/bin/bash

# заходит на аппарат
# делает снимок
# достает снимок на комп

echo 'запуск скрипта'
ssh pi@10.3.141.1 'raspistill -o ~/shots/calibration_00.jpg'
mkdir ~/shots_from_boat
scp pi@10.3.141.1:~/shots/calibration_00.jpg ~/shots_from_boat/image.jpg
python3 ./try_crop.py ~/shots_from_boat/image.jpg
echo 'скрипт выполнен'
