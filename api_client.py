import aiohttp
from config import API_BASE_URL, SEED_STRING, SENDER_ADDRESS, WALLET_VERSION

class StarsAPI:
    def __init__(self):
        self.base_url = API_BASE_URL

    async def buy_stars(self, username: str, amount: int) -> dict:
        """
        Покупка Stars через API Fragment
        """
        url = f"{self.base_url}/api/v1/stars/buy"
        
        payload = {
            "seed": SEED_STRING,
            "sender_address": SENDER_ADDRESS,
            "wallet_version": WALLET_VERSION,
            "amount": amount,
            "payment_method": "ton",
            "show_sender": True,
            "username": username
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                data = await resp.json()
                if resp.status == 200:
                    return {"success": True, "data": data}
                else:
                    return {"success": False, "error": data.get("error", "Неизвестная ошибка")}

    async def gift_premium(self, username: str, months: int) -> dict:
        """
        Подарок Premium (дополнительно)
        """
        url = f"{self.base_url}/api/v1/premium/gift"
        
        payload = {
            "seed": SEED_STRING,
            "sender_address": SENDER_ADDRESS,
            "wallet_version": WALLET_VERSION,
            "months": months,
            "payment_method": "ton",
            "show_sender": True,
            "username": username
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                data = await resp.json()
                if resp.status == 200:
                    return {"success": True, "data": data}
                else:
                    return {"success": False, "error": data.get("error", "Неизвестная ошибка")}