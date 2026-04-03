import asyncio
from app.config import settings

class RconProtocol(asyncio.DatagramProtocol):
    def __init__(self, message, on_con_lost):
        self.message = message
        self.on_con_lost = on_con_lost
        self.transport = None
        self.response = b""

    def connection_made(self, transport):
        self.transport = transport
        self.transport.sendto(self.message)

    def datagram_received(self, data, addr):
        # Every Quake 3 RCON packet starts with \xff\xff\xff\xffprint\n
        # (or \xff\xff\xff\xffstatusResponse\n for unauthenticated getstatus)
        print(f"DEBUG: Received RCON packet ({len(data)} bytes) from {addr}")
        if data.startswith(b"\xff\xff\xff\xffprint\n"):
            self.response += data[10:]
        elif data.startswith(b"\xff\xff\xff\xff"):
            # Try to skip headers of various lengths (some engines send \xff\xff\xff\xff without 'print')
            # Look for the first newline or just keep it all for regex later
            self.response += data[4:]
        else:
            self.response += data

    def error_received(self, exc):
        print('Error received:', exc)

    def connection_lost(self, exc):
        if not self.on_con_lost.done():
            self.on_con_lost.set_result(self.response)

async def send_rcon_command(command: str, timeout: float = 2.0) -> str:
    """
    Sends an RCON command to the server and returns the response.
    """
    loop = asyncio.get_running_loop()
    on_con_lost = loop.create_future()
    
    # Prefix: 4x 0xFF + "rcon " + password + " " + command + \n
    message = b"\xff\xff\xff\xffrcon " + settings.rcon_password.encode() + b" " + command.encode() + b"\n"
    
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: RconProtocol(message, on_con_lost),
        remote_addr=(settings.rcon_host, settings.rcon_port)
    )

    try:
        # Wait for the response with a timeout
        try:
            async with asyncio.timeout(timeout):
                last_response_len = 0
                while True:
                    await asyncio.sleep(0.1)
                    # If we have some data and it hasn't changed for 100ms, assume we're done
                    if len(protocol.response) > 0 and len(protocol.response) == last_response_len:
                        break
                    # If we've waited but still have no data, continue until timeout
                    last_response_len = len(protocol.response)
                    if last_response_len > 100000: # Safety cap
                        break
        except TimeoutError:
            print(f"RCON Timeout after {timeout}s for command: {command}")
        except asyncio.CancelledError:
            pass
    finally:
        transport.close()

    response_data = protocol.response
    return response_data.decode("utf-8", errors="ignore").strip()
