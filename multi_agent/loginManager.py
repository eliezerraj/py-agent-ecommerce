import logging
import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SESSION_TIMEOUT = 30
session_timeout = aiohttp.ClientTimeout(total=SESSION_TIMEOUT)

class LoginManager:

    def __init__(self):
        self.logged_in = False
        self.user_token = None
        self.username = None

    async def login(self, username: str, password: str) -> bool:

        headers = {"Content-Type": "application/json"}
        url = f"https://go-api-global.architecture.caradhras.io/identidy/oauth_credential"

        payload = {
            "user" :username,
            "password": password,
        }

        async with aiohttp.ClientSession(timeout=session_timeout) as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    self.logged_in = True
                    self.user_token = data.get("token")        
                    self.username = username
                    return True
                else:
                    logger.warning(f"Login failed {resp.status}")
                    return False


    def is_authenticated(self) -> bool:
        return self.logged_in

    def get_token(self):
        return self.user_token
