from fastapi.routing import APIRouter
from pydantic import BaseModel

from api.helpers.database import CardsCollection

router = APIRouter()


class Sets(BaseModel):
    sets: list[str]


@router.get("/sets")
def get_sets(collection: CardsCollection) -> Sets:
    """Get all unique MTG set names.

    Args:
        collection: MongoDB cards collection (injected dependency)

    Returns:
        Sets object containing list of unique set names.
    """
    sets = [
        card_set["_id"]
        for card_set in collection.aggregate(
            [
                {
                    "$group": {
                        "_id": "$set_name",
                    }
                },
                {"$sort": {"_id": 1}},  # 1 for ascending (alphabetical) order
            ]
        )
    ]

    return {"sets": sets}
