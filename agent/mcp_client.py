import asyncio
import sys
import threading
from contextlib import AsyncExitStack
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVEUR = Path(__file__).resolve().parent.parent / "mcp_server" / "server.py"


class ClientMCP:
    def __init__(self):
        self._loop = asyncio.new_event_loop()
        threading.Thread(target=self._loop.run_forever, daemon=True).start()
        self._stack = AsyncExitStack()
        self._session = None
        self._executer(self._connecter(), timeout=180)

    def _executer(self, coro, timeout=120):
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result(timeout=timeout)

    async def _connecter(self):
        params = StdioServerParameters(command=sys.executable, args=[str(SERVEUR)])
        lecture, ecriture = await self._stack.enter_async_context(stdio_client(params))
        self._session = await self._stack.enter_async_context(ClientSession(lecture, ecriture))
        await self._session.initialize()

    def lister_outils(self) -> list[dict]:
        """Outils du serveur, au format function calling de l'API OpenAI."""
        res = self._executer(self._session.list_tools())
        return [{"type": "function",
                 "function": {"name": t.name, "description": t.description or "",
                              "parameters": t.inputSchema}} for t in res.tools]

    def appeler(self, nom: str, arguments: dict) -> str:
        res = self._executer(self._session.call_tool(nom, arguments))
        texte = "\n".join(c.text for c in res.content if getattr(c, "type", "") == "text")
        return f"Erreur de l'outil : {texte}" if res.isError else texte


_instance = None
_verrou = threading.Lock()


def get_mcp() -> ClientMCP:
    global _instance
    with _verrou:
        if _instance is None:
            _instance = ClientMCP()
        return _instance