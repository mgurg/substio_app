from typing import Any, TypeVar

from sqlalchemy import Sequence, and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.models import BaseModel

T = TypeVar("T", bound=BaseModel)


class GenericRepo[T]:
    def __init__(self, session: AsyncSession, model: type[T]):
        """
        Initializes the repository with the given session and model.

        :param session: The SQLAlchemy session to use.
        :param model: The SQLAlchemy model to use.
        """
        self.session = session
        self.model = model

    async def get_all(self) -> Sequence[T]:
        """
        Retrieves all objects from the database.

        :return: A list of all objects of the model type.
        """
        result = await self.session.execute(select(self.model))
        return result.scalars().all()

    async def get_by_id(self, id: int) -> T | None:
        """
        Retrieves an object by its ID.

        :param id: The ID of the object to retrieve.
        :return: The object if found, None otherwise.
        """
        result = await self.session.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def create(self, **kwargs: dict[str, Any]) -> T:
        """
        Creates a new object with the given keyword arguments.

        :param kwargs: The keyword arguments to use for creating the object.
        :return: The newly created object.
        """
        obj = self.model(**kwargs)
        self.session.add(obj)
        await self.session.commit()  # await commit
        await self.session.refresh(obj)  # await refresh

        return obj

    async def create_all(self, data_list: list[dict[str, Any]]) -> None:
        for user_data in data_list:
            obj = self.model(**user_data)
            self.session.add(obj)
        await self.session.commit()  # await commit

    async def update(self, id: int, **kwargs: dict[str, Any]) -> None:
        """
        Updates an object with the given ID and keyword arguments.
        """
        await self.session.execute(update(self.model).where(self.model.id == id).values(**kwargs))  # await update
        await self.session.commit()  # await commit

    async def delete(self, id: int) -> T | None:
        """
        Deletes an object by its ID.

        :param id: The ID of the object to delete.
        :return: The deleted object if found, None otherwise.
        """
        obj = await self.get_by_id(id)  # await get_by_id
        if obj:
            await self.session.delete(obj)  # await delete
            await self.session.commit()  # await commit
        return obj

    async def filter(self, page: int = 1, per_page: int = 10, **kwargs: dict[str, Any]) -> Sequence[T]:
        """
        Filters objects based on the given keyword arguments and paginate the result.
        """
        offset = (page - 1) * per_page
        filters = [getattr(self.model, k) == v for k, v in kwargs.items()]
        query = select(self.model).where(and_(*filters)).limit(per_page).offset(offset)
        result = await self.session.execute(query)  # await the query
        return result.scalars().all()
