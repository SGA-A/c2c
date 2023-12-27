from typing import Literal, Any
import shelve


def get_profile_key_value(key: str) -> Any:
    """Fetch a profile key (attribute) from the database. Returns None if no key is found."""
    with shelve.open("C:\\Users\\georg\\PycharmProjects\\c2c\\db-shit\\profile_mods") as dbmr:
        return dbmr.setdefault(key, None)


def modify_profile(typemod: Literal["update", "create", "delete"], key: str, new_value: Any):
    """Modify custom profile attributes (or keys) of any given discord user. If "delete" is used on a key that does not exist, returns ``0``
    :param typemod: type of modification to the profile. could be ``update`` to update an already existing key, or ``create`` to create a new key or ``delete`` to delete a key
    :param key: The key to modify/delete.
    :param new_value: The new value to replace the old value with. For a typemod of ``delete``, this argument will not matter at all, since only the key name is required to delete a key."""
    with shelve.open("C:\\Users\\georg\\PycharmProjects\\c2c\\db-shit\\profile_mods") as dbm:
        match typemod:
            case "update" | "create":
                dbm.update({f'{key}': new_value})
                return dict(dbm)
            case "delete":
                try:
                    del dbm[f"{key}"]
                except KeyError:
                    return 0
            case _:
                return "invalid type of modification value entered"

val: str = get_profile_key_value(f"546086191414509599 badges")
print(val)
new_val = val.replace("<:blobsm:1154477660555182185>", "<:in_power:1153754243220647997>")
print(modify_profile("update", "546086191414509599 badges", new_val))
