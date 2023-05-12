"""A module to handle the database."""

import os
from tinydb import TinyDB, Query

if not os.path.isdir("./data"):
    os.makedirs("./data")
db: TinyDB = TinyDB('./data/db.json')


def insert_guild(guild_id: int, name: str):
    """Insert a guild to database.

    Args:
        guild_id (int): guild_id of dicsord
        name     (str): name of the guild

    Returns:
        Inserted guild.
    """

    table = db.table("guilds")
    if table.search(Query().guild_id == guild_id) == []:
        table.insert({
            "guild_id":  guild_id,
            "name":      name,
            "read_name": True,
            "read_bot":  True,
        })

    return table.search(Query().guild_id == guild_id)[0]


def update_guild(guild_id: int, value: dict):
    """Update a guild in database.

    Args:
        guild_id (int) : guild_id of discord
        value    (dict): update params

    Returns:
        Updated guild.
    """

    table = db.table("guilds")

    return table.update(value, Query().guild_id == guild_id)


def search_guild(guild_id: int):
    """Search a guild in database

    Args:
        guild_id (int): guild_id of discord

    Returns:
        If found, return guild.
    """

    table = db.table("guilds")
    guild = table.search(Query().guild_id == guild_id)
    if guild == []:
        return None

    return guild[0]


def insert_user(user_id: int, name: str):
    """Insert a user to database.

    Args:
        user_id (int): user_id of dicsord
        name     (str): name of the user

    Returns:
        Inserted user.
    """

    table = db.table("users")
    if table.search(Query().user_id == user_id) == []:
        table.insert({
            "user_id":       user_id,
            "name":          name,
            "speaker":       "show",
            "pitch":         100,
            "speed":         100,
            "emotion":       "",
            "emotion_level": 2,
        })

    return table.search(Query().user_id == user_id)[0]


def update_user(user_id: int, value: dict):
    """Update a guild in database.

    Args:
        user_id (int) : user_id of discord
        value   (dict): update params

    Returns:
        Updated user.
    """

    table = db.table("users")

    return table.update(value, Query().user_id == user_id)


def search_user(user_id: int):
    """Search a user in database

    Args:
        user_id (int): user_id of discord

    Returns:
        If found, return user.
    """

    table = db.table("users")
    user = table.search(Query().user_id == user_id)
    if user == []:
        return None

    return user[0]


def insert_dictionary(guild_id: int, word: str, read: str):
    """Insert a user to database.

    Args:
        guild_id (int): guild_id of dicsord
        word     (str): word to add
        read     (str): how to read the word

    Returns:
        Inserted dictionary.
    """

    table = db.table("dictionaries")
    inserted_doc_id = table.insert({
        "guild_id": guild_id,
        "word":     word,
        "read":     read,
    })

    return table.get(doc_id=inserted_doc_id)


def delete_dictionary(guild_id: int, doc_id: int):
    """Delete a word in dictionary

    Args:
        guild_id (int): guild_id of discord
        doc_id   (int): doc_id of the word to delete

    Returns:
        Deleted word if success.
    """

    table = db.table("dictionaries")

    dictionary = table.get(doc_id=doc_id)

    if dictionary is not None:
        if dictionary["guild_id"] == guild_id:
            table.remove(doc_ids=[doc_id])
        else:
            return None

    return dictionary


def search_dictionary(guild_id: int, doc_id: int | None = None):
    """Search words in dictionary table

    Args:
        guild_id (int): guild_id of discord

    Returns:
        If found, return words.
    """

    table = db.table("dictionaries")
    dictionaries = table.search(Query().guild_id == guild_id)

    return dictionaries
