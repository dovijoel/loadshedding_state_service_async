from typing import List

import requests
from aiohttp import ClientSession


class LoadsheddingAPI:

    def __init__(
            self,
            session: ClientSession,
            api_key: str,
            base_url: str = "https://developer.sepush.co.za/business/2.0",
            test: str = None
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.test = test
        self.headers = {
            "token": self.api_key
        }
        self.session = session
        self.session.headers.update(self.headers)

    async def get_loadshedding_status(self) -> dict:
        # TODO account for cape town
        url = f"{self.base_url}/status"
        params = {}
        if self.test is not None:
            params['test'] = self.test
        response = await self.session.get(url, params=params)
        response_json: dict = await response.json()
        loadshedding_status = response_json['status']['eskom']
        return loadshedding_status

    async def get_area_information(self, block_id: str) -> dict:
        url = f"{self.base_url}/area"
        params = {'block_id': block_id}
        if self.test is not None:
            params['test'] = self.test
        response = await self.session.get(url, params=params)
        response_json: dict = await response.json()
        return response_json

    async def get_areas_text_search_results(self, search_term: str) -> List[dict]:
        url = f"{self.base_url}/areas_search"
        params = {'text': search_term}
        response = await self.session.get(url, params=params)
        response_json: dict = await response.json()
        return response_json['areas']

    async def get_areas_gps_search_results(self, latitude: float, longitude: float) -> List[dict]:
        url = f"{self.base_url}/areas_nearby"
        params = {'latitude': latitude, 'longitude': longitude}
        response = await self.session.get(url, params=params)
        response_json: dict = await response.json()
        return response_json['areas']

    async def get_quota(self):
        url = f"{self.base_url}/api_allowance"
        response = await self.session.get(url)
        response_json: dict = await response.json()
        return response_json['allowance']

