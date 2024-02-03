import zlib

def on_websocket_message(msg):
  buffer = bytearray()
  buffer.extend(msg)
  if len(msg) < 4 or msg[-4:] != ZLIB_SUFFIX:
    return
  return inflator.decompress(buffer)

ZLIB_SUFFIX = b'\x00\x00\xff\xff'
inflator = zlib.decompressobj()

with open("webSocketData1.txt", "r") as file:
  cont = file.read()
  with open("webSocketData1_decoded.txt", "wb") as f:
    f.write(on_websocket_message(bytes.fromhex(cont)))