from pydantic import BaseModel
from typing import Optional


class TenderFeild(BaseModel):
    value : Optional[str]
    confidence : float
    page : Optional[int]
    extraction_method : str


class TenderData(BaseModel):
    tender_number: TenderFeild
    end_amount : TenderFeild
    bid_due_date : TenderFeild


