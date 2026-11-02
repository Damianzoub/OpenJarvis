"""Pretend ESP32: speaks firmware/PROTOCOL.md v1 using the laptop mic and speakers.

Usage:
    python evals/test/fake_device.py [ws://localhost:8000/ws/voice]

Press Enter to start talking, Enter again to stop (push-to-talk).
"""

import asyncio
import json
import os
import socket
import sys
import threading

import sounddevice as sd
from websockets.asyncio.client import connect

SAMPLE_RATE = 16000
FRAME_SAMPLES = 320  # 20 ms -> 640 bytes of PCM16, as the protocol requires

URL = sys.argv[1] if len(sys.argv) > 1 else "ws://localhost:8000/ws/voice"
TOKEN = os.getenv("DEVICE_TOKEN", "dev")
DEVICE_ID = f"fake-{socket.gethostname()}"


async def main() -> None:
    loop = asyncio.get_running_loop()
    # Audio frames and button events share one queue so they reach the server in order.
    outgoing: asyncio.Queue[bytes | str] = asyncio.Queue()
    talking = False

    playback = bytearray()
    playback_lock = threading.Lock()

    def on_mic(indata, frames, time, status) -> None:
        if talking:
            loop.call_soon_threadsafe(outgoing.put_nowait, bytes(indata))

    def on_speaker(outdata, frames, time, status) -> None:
        n = len(outdata)
        with playback_lock:
            chunk = bytes(playback[:n])
            del playback[:n]
        outdata[: len(chunk)] = chunk
        outdata[len(chunk) :] = b"\x00" * (n - len(chunk))

    def clear_playback() -> None:
        with playback_lock:
            playback.clear()

    def toggle_button() -> None:
        nonlocal talking
        talking = not talking
        if talking:
            clear_playback()  # barge-in: stop speaking immediately, don't wait for the server
            outgoing.put_nowait(json.dumps({"type": "button_down"}))
            print("[device] talking... (Enter to stop)")
        else:
            outgoing.put_nowait(json.dumps({"type": "button_up"}))
            print("[device] stopped")

    def read_keyboard() -> None:
        for _ in sys.stdin:
            loop.call_soon_threadsafe(toggle_button)

    async def send_loop(ws) -> None:
        while True:
            await ws.send(await outgoing.get())

    async with connect(f"{URL}?device_id={DEVICE_ID}&token={TOKEN}") as ws:
        await ws.send(json.dumps({
            "type": "hello",
            "v": 1,
            "device_id": DEVICE_ID,
            "fw_version": "fake-0.1",
            "capabilities": ["mic", "speaker", "button"],
        }))
        ready = json.loads(await ws.recv())
        if ready.get("type") != "ready":
            print(f"[device] expected ready, got {ready}")
            return
        print(f"[device] connected, session={ready.get('session_id')}. Press Enter to talk.")

        mic = sd.RawInputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                                blocksize=FRAME_SAMPLES, callback=on_mic)
        speaker = sd.RawOutputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                                     callback=on_speaker)
        threading.Thread(target=read_keyboard, daemon=True).start()
        sender = asyncio.create_task(send_loop(ws))

        with mic, speaker:
            async for message in ws:
                if isinstance(message, bytes):
                    with playback_lock:
                        playback.extend(message)
                    continue
                print(f"[server] {message}")
                if json.loads(message).get("type") == "clear":
                    clear_playback()

        sender.cancel()
        print("[device] server closed the connection")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
