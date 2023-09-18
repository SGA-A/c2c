
word = "<:giftcard:1153374718863347792> Keycard"

def item_exists() -> bool:
    if "Keycard" in word:
        return True
    return False

if item_exists():
    print("Nice")