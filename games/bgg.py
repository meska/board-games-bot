"""
Board Game Geek API
"""
from typing import Optional

import aiohttp
import xmltodict
from munch import munchify

API_URL = "https://boardgamegeek.com/xmlapi2"


def extract_suggested(game_data: dict) -> Optional[str]:
    """
    Extract suggested players from game data
    """
    normalized_data = {}

    for poll in game_data['items']['item']['poll']:
        if poll['@name'] == "suggested_numplayers":
            for result in poll['results']:
                # extract best result
                normalized_data[result['@numplayers']] = int(result['result'][0]['@numvotes'])

    if normalized_data:
        return max(normalized_data, key=normalized_data.get)

    return None


async def get_game(game_id: int) -> Optional[object]:
    """
    Get game info from BGG
    """
    url = f"{API_URL}/thing/"
    params = {
        "id": game_id, "stats": "1",
        "videos": "0",
        "historical": "0",
        "marketplace": "0",
        "comments": "0",
        "ratingcomments": "0"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                xml = await response.text()
                game_data = xmltodict.parse(xml)
                if isinstance(game_data['items']['item']['name'], list):
                    name = game_data['items']['item']['name'][0]['@value']
                else:
                    name = game_data['items']['item']['name']['@value']

                if game_data['items'].get('item'):
                    return munchify({
                        "id": game_data['items']['item']['@id'],
                        "name": name,
                        "type": game_data['items']['item']['@type'],
                        "year": game_data['items']['item']['yearpublished']['@value'],
                        "minplayers": game_data['items']['item']['minplayers']['@value'],
                        "maxplayers": game_data['items']['item']['maxplayers']['@value'],
                        "rating": game_data['items']['item']['statistics']['ratings']['average']['@value'],
                        "playingtime": game_data['items']['item']['playingtime']['@value'],
                        "suggested_players": extract_suggested(game_data),
                        "thumbnail": game_data['items']['item'].get('thumbnail'),
                        "url": f"https://boardgamegeek.com/{game_data['items']['item']['@type']}/{game_data['items']['item']['@id']}"
                    })
                return None
            else:
                return None


async def search_game(query: str) -> list:
    """
    Get game info from BGG
    """
    url = f"{API_URL}/search"
    params = {
        "query": query,
        "type": "boardgame",
    }
    out = []
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                xml = await response.text()
                res = xmltodict.parse(xml)
                if res['items']['@total'] == "1":
                    item = res['items']['item']
                    out.append(
                        munchify({
                            "id": item['@id'],
                            "type": item['@type'],
                            "name": item['name']['@value'],
                            "year": item['yearpublished']['@value'] if item.get('yearpublished') else None,
                        })
                    )
                    return out
                if res['items']['@total'] != "0":
                    for item in res['items']['item']:
                        out.append(
                            munchify({
                                "id": item['@id'],
                                "type": item['@type'],
                                "name": item['name']['@value'],
                                "year": item['yearpublished']['@value'] if item.get('yearpublished') else None,
                            })
                        )
                    return out
    return out
