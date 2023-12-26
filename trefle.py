import random

items = set()
total = 0
counter = 0
for _ in range(1000):
    for y in range(10):
        total += random.randint(1, 5)
        if total >= 100:
            items.add(counter)
            continue
        counter += 1


length = len(items)
a = [item for item in items]
print(a[0])
tot = sum(items)
mean = tot / length
print(mean)
