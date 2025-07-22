from decimal import Decimal
from app.db.dynamodb import get_table
from fastapi import HTTPException

def get_user_credits(user_id: str) -> int:
    table = get_table("users")
    user = table.get_item(Key={"user_id": user_id}).get("Item")
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.get("credits", 0)

def decrement_user_credits(user_id: str):
    table = get_table("users")

    # Fetch current credits
    user_item = table.get_item(Key={"user_id": user_id}).get("Item")
    if not user_item:
        raise HTTPException(status_code=404, detail="User not found")

    current_credits = int(user_item.get("credits", 0))
    if current_credits <= 0:
        raise HTTPException(status_code=402, detail="Out of credits")

    new_credits = current_credits - 1

    table.update_item(
        Key={"user_id": user_id},
        UpdateExpression="SET credits = :new_credits",
        ExpressionAttributeValues={":new_credits": Decimal(new_credits)}
    )
