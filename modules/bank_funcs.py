import aiosqlite

from typing import Tuple, Any, Optional

__all__ = [
    "DB",
]

class Database:
    def __init__(self):
        self.conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        try:
            self.conn = await aiosqlite.connect("economy.db")
        except aiosqlite.Error:
            pass

    @property
    def is_connected(self) -> bool:
        return self.conn is not None

    @staticmethod
    async def _fetch(cursor, mode) -> Optional[Any]:
        if mode == "one":
            return await cursor.fetchone()
        if mode == "many":
            return await cursor.fetchmany()
        if mode == "all":
            return await cursor.fetchall()

        return None

    async def execute(self, query: str, values: Tuple = (), *, fetch: str = None) -> Optional[Any]:
        cursor = await self.conn.cursor()

        await cursor.execute(query, values)
        data = await self._fetch(cursor, fetch)
        await self.conn.commit()

        await cursor.close()
        return data


DB = Database()

