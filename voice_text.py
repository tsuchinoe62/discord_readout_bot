import os
import aiohttp
import datetime

SPEAKER_LIST = ["show", "haruka", "hikari", "takeru", "santa", "bear"]
EMOTION_LIST = ["happiness", "anger", "sadness"]


def adjust_value(value: int, min: int, max: int):
    if value < min:
        return min
    elif value > max:
        return max
    else:
        return value


def save_tmp_file(bin: bytes, format: str):
    now = datetime.datetime.now().strftime("%Y%m%d-%H%M%S%f")

    filename = f"{now}.{format}"
    tmp = "./cache/"
    if not os.path.isdir(tmp):
        os.makedirs(tmp)

    with open(tmp + filename, mode="wb") as f:
        f.write(bin)

    return tmp + filename


async def fetch(client: aiohttp.ClientSession, api_key: str, params: dict):
    url: str = "https://api.voicetext.jp/v1/tts"
    async with client.post(url, auth=aiohttp.BasicAuth(api_key, ""), data=params) as response:
        if response.status != 200:
            print("Error API : " + str(response.status))
            print(await response.json())

        return await response.read()


async def call_api(api_key: str, text: str, speaker: str = "show", format: str = "wav", emotion: str = None, emotion_level: int = 2, pitch: int = 100, speed: int = 100, volume: int = 100):
    FORMAT_LIST = ["wav", "ogg", "mp3"]

    params: dict = {
        "text": text[:200],
        "speaker": speaker if speaker in SPEAKER_LIST else "show",
        "format": format if format in FORMAT_LIST else "wav",
        "pitch": adjust_value(pitch, 50, 200),
        "speed": adjust_value(speed, 50, 400),
        "volume": adjust_value(volume, 50, 200),
    }

    if emotion in EMOTION_LIST and params["speaker"] in ["haruka", "hikari", "takeru", "santa", "bear"]:
        params["emotion"] = emotion
        params["emotion_level"] = adjust_value(emotion_level, 1, 4)

    async with aiohttp.ClientSession() as client:
        bin = await fetch(client, api_key=api_key, params=params)

    voice_file = save_tmp_file(bin, format)

    return voice_file
