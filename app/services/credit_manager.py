from decimal import Decimal
from botocore.exceptions import ClientError
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

    # Atomic conditional decrement — no read-modify-write race, rejects at 0
    try:
        table.update_item(
            Key={"user_id": user_id},
            UpdateExpression="ADD credits :neg_one",
            ConditionExpression="credits > :zero",
            ExpressionAttributeValues={
                ":neg_one": Decimal(-1),
                ":zero": Decimal(0)
            }
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise HTTPException(status_code=402, detail="Out of credits")
        raise
