import asyncio

async def main(config):

  while True:
    try:
      print("Trigger task is running")
      await asyncio.sleep(1)
    except asyncio.CancelledError:
      print("Terminating trigger task.")
      break
