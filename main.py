# pip install FlightRadarAPI

import asyncio
from typing import List

import FlightRadar24
import aiohttp
from FlightRadar24 import FlightRadar24API
from loguru import logger as log


area_of_interest = {"latitude": 43.533321723, "longitude": 33.245738826, "radius": 345000}

DEBUG = False


class Flight:
    def __init__(self, callsign):
        self.callsign = callsign
        self.squawk = ""
        self.present = False

    def update_squawk(self, new_squawk):
        if self.squawk != new_squawk:
            self.squawk = new_squawk
            return True
        return False


class ForteTracker:
    def __init__(self, webhooks: List[str]):
        self.fr_api = FlightRadar24API()
        self.tracked_flights = {"FORTE10": Flight("FORTE10")}
        log.success("Forte tracker initialized")
        self.webhooks = webhooks

    async def send_discord_alert(self, message):
        if DEBUG:
            print(message)
            return
        data = {"content": message}
        async with aiohttp.ClientSession() as session:
            for webhook in self.webhooks:
                async with session.post(webhook, json=data) as response:
                    if response.status != 204:
                        print(f"Failed to send webhook message: {response.status}, {await response.text()}")

    @staticmethod
    def find_flight(callsign: str, flights: List[FlightRadar24.Flight]):
        return next(
            (flight for flight in flights if callsign == flight.callsign), None
        )

    async def get_forte(self):
        bounds = self.fr_api.get_bounds_by_point(**area_of_interest)
        flights = self.fr_api.get_flights(bounds=bounds)

        for flight in self.tracked_flights.values():
            if cur_flight := self.find_flight(flight.callsign, flights):
                if not flight.present:
                    # new_flight_detected
                    flight.present = True
                    await self.send_discord_alert(f":airplane: {flight.callsign} has entered the black sea: [{cur_flight.latitude}, {cur_flight.longitude}]")
                else:
                    print("flight detected but state did not change")
                if flight.update_squawk(cur_flight.squawk):
                    # squawk_changed
                    await self.send_discord_alert(f"ALERT! New squawk for {flight.callsign}: {flight.squawk}")

            elif flight.present:

                flight.present = False
                await self.send_discord_alert(f":airplane: {flight.callsign} has left the area")


    async def run(self):
        while True:
            await self.get_forte()
            await asyncio.sleep(300)


if __name__ == '__main__':
    _webhooks = []
    ft = ForteTracker(_webhooks)
    asyncio.run(ft.run())
