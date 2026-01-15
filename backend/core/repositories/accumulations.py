import datetime
from typing import List, Optional

from bson import ObjectId

from core.dtos.accumulations import AccumulationBody
from core.dtos.pagination import CursorPage, PaginationParams
from core.models.accumulations import (
    Accumulation,
    AccumulationReportView,
    AccumulationsInPeriod,
)
from core.utils.pagination import Paginator


class AccumulationRepository:
    async def get_accumulations_paginated(
        self, pagination: Optional[PaginationParams], search: Optional[str] = None
    ) -> CursorPage[Accumulation]:
        search_query = {}
        if search:
            search_query = {
                "$or": [
                    {"customer.phone_number": {"$regex": search, "$options": "i"}},
                    {"customer.name": {"$regex": search, "$options": "i"}},
                    {"customer.last_name": {"$regex": search, "$options": "i"}},
                    {
                        "$expr": {
                            "$regexMatch": {
                                "input": {
                                    "$concat": [
                                        "$customer.name",
                                        " ",
                                        "$customer.last_name",
                                    ]
                                },
                                "regex": search,
                                "options": "i",
                            }
                        }
                    },
                ]
            }
        return await Paginator(Accumulation, pagination).paginate(
            search_query, fetch_links=True, on_demand=False
        )

    async def get_accumulations_report_paginated(
        self, pagination: Optional[PaginationParams]
    ) -> CursorPage[AccumulationReportView]:
        return await Paginator(AccumulationReportView, pagination).paginate(
            fetch_links=True
        )

    async def get_accumulations_report_in_period(
        self,
        customer_id: str,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> AccumulationsInPeriod | None:
        accumulation_report = (
            await Accumulation.find(
                Accumulation.customer.id == ObjectId(customer_id),
                Accumulation.created_at >= start_date,
                Accumulation.created_at <= end_date,
            )
            .aggregate(
                [
                    {
                        "$group": {
                            "_id": "$customer.$id",
                            "total": {"$sum": "$generated_points"},
                            "total_transactions": {"$sum": 1},
                        }
                    }
                ],
                projection_model=AccumulationsInPeriod,
            )
            .to_list()
        )

        return accumulation_report[0] if accumulation_report else None

    async def create_accumulation(self, accum: Accumulation) -> Accumulation:
        accum = await accum.create()
        await accum.fetch_all_links()
        return accum

    async def last_accumulation_threshold(
        self, accumulation: AccumulationBody, threshold=1
    ):
        now = datetime.datetime.now() - datetime.timedelta(minutes=threshold)
        accumulation_ = await Accumulation.find_one(
            Accumulation.product.codename == accumulation.product_codename,
            Accumulation.amount == accumulation.amount,
            Accumulation.customer.phone_number == accumulation.customer_phone,
            Accumulation.gas_station.external_id
            == accumulation.external_gas_station_id,
            Accumulation.created_at >= now,
            fetch_links=True,
        )

        return accumulation_


accumulation_repository = AccumulationRepository()
