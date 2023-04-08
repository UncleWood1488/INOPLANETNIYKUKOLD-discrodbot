import random

start = 1
print(f"Угадай число от {start} до ? \n")

end = int(input("Введите число: "))
print()

while True:
    #print(f"var end is: {end}")
    if end > 9999:
        print("ОШИБКА! максимальное возможное число не больше 9999 \n")
        end = int(input("Введите число: "))
    else:
        break

print(f"Угадай число от 1 до {end} \n")

print("Идёт подсчёт...\n")
randomnumber = random.randint(start,end)
usernumber = int(input("Введите число для ответа: "))
print()

if usernumber == randomnumber:
    print(f"Победа {randomnumber}")
else:
    print(f"Поражение {randomnumber} \n")

print("Завершение работы")