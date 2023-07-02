import os.path
import re
from string import Template
from typing import Any

import httpx
from tqdm import tqdm

from models.Clip import Clip


class TwitchScraper:
    GET_TOKEN_URL: str = 'https://id.twitch.tv/oauth2/token'
    GET_USER_URL: Template = Template('https://api.twitch.tv/helix/users?login=$login')
    GET_CLIPS_URL: Template = Template(
        'https://api.twitch.tv/helix/clips?broadcaster_id=$broadcaster&first=30&after=$after')

    def __init__(self, api_key: str, api_secret: str, api_token: str):
        self._api_key: str = api_key
        self._api_secret: str = api_secret
        self._api_token: str = api_token

    def __get_token(self) -> None:
        print('Getting new token for %s', self._api_key)

        token_params: dict[str, str] = {'client_id': self._api_key,
                                        'client_secret': self._api_secret,
                                        'grant_type': 'clent_credentials'}

        try:
            response: httpx.Response = httpx.post(url=self.GET_TOKEN_URL, params=token_params)
            response.raise_for_status()

            d: dict[str, str] = response.json()
            self._api_token = d['access_token']

        except httpx.HTTPError as exc:
            print(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}.")

    def request_with_auth(self, url: str) -> dict[str, Any]:

        if not self._api_token:
            print('Token not found')
            self.__get_token()

        headers: dict[str, str] = {'Client-Id': self._api_key,
                                   'Authorization': f'Bearer {self._api_token}'}

        try:
            response: httpx.Response = httpx.get(url=url, headers=headers)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPError as exc:
            print(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}.")

    def get_user(self, username: str) -> str:

        get_user_url = self.GET_USER_URL.substitute(login=username)

        response_json: dict[str, Any] = self.request_with_auth(get_user_url)
        user_data: list[dict[str, str]] = response_json['data']

        if len(user_data) == 0:
            print(f'User {username} not found on Twitch')
            return

        return user_data[0].get('id')

    def get_all_clips(self, broadcaster: str) -> None:

        after: str = ''

        while after is not None:
            get_clips_url = self.GET_CLIPS_URL.substitute(broadcaster=broadcaster, after=after)
            response_json: dict[str, Any] = self.request_with_auth(get_clips_url)

            pagination: dict[str, str] = response_json.get('pagination')
            after = pagination.get('cursor')

            clips_data: list[dict[str, str | int]] = response_json.get('data')

            if len(clips_data) == 0:
                print(f'No clips found for {broadcaster}')
                break

            clips: list[Clip] = list(map(Clip.model_validate, clips_data))
            print(f'Downloading {len(clips)} clips')

            list(map(self.download_clip, clips))

    @staticmethod
    def download_clip(clip: Clip):

        url: str = re.sub('-preview.*', '.mp4', clip.thumbnail_url)
        clip_path: str = f'{clip.created_at.strftime("%Y%m%d%H%M%S")}-{clip.title}.mp4'
        clip_path = re.sub('[<>:*|?/"\\\\]', '', clip_path)
        clip_path = f'Downloads/{clip_path}'

        with httpx.stream("GET", url) as response:
            total = int(response.headers["Content-Length"])

            if os.path.exists(clip_path) and os.stat(clip_path).st_size == total:
                return

            with open(clip_path, 'wb') as download_file:
                with tqdm(total=total, unit_scale=True, unit_divisor=1024, unit="B", desc=clip_path) as progress:
                    num_bytes_downloaded = response.num_bytes_downloaded
                    for chunk in response.iter_bytes():
                        download_file.write(chunk)
                        progress.update(response.num_bytes_downloaded - num_bytes_downloaded)
                        num_bytes_downloaded = response.num_bytes_downloaded
