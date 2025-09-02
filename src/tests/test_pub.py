
import asyncio
import json
from aio_pika import connect_robust, Message, DeliveryMode

amqp_url="amqp://admin:admin1234@95.110.228.29:5672"
async def send_command_to_device(device_id: str, command: str):
    connection = await connect_robust(amqp_url)
    channel = await connection.channel()

    exchange = await channel.declare_exchange(
        name="device.exchange",
        type="direct",
        durable=True
    )
    [["Test #", "1"], ["Result", "+"], ["Purity", "95%"], ["Type", "Grain"]]
    message_body = json.dumps({
        "type": command,
        "Test#": "C5627272",
        "Result": "Positive",
        "Level": "10-15pbb",
        "Purity":"95%",
        "Type":"Maize",
        "Count": "200",
        
    }).encode()

    await exchange.publish(
        Message(
            body=message_body,
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT
        ),
        routing_key=device_id
    )

    print(f"✅ Sent '{command}' command to device {device_id}")
    await connection.close()
def dict_to_ordered_key_value_list(item: dict, ordered_keys: list) -> list[list]:
            return [
                [key, value] for key in ordered_keys
                if (value := item.get(key)) not in [None, "", "N/A"]
            ]
class LIFOStorage:
    def __init__(self, max_size: int = 100):
        self.stack = []
        self.max_size = max_size

    def push(self, item):
        if len(self.stack) >= self.max_size:
            self.stack.pop(0)  # Remove oldest to maintain max size (optional)
        self.stack.append(item)

    def pop(self):  # Hard pop (removes)
        if self.stack:
            return self.stack.pop()
        return None

    def peek(self):  # Soft pop (just view top item)
        if self.stack:
            return self.stack[-1]
        return None

    def peek_all(self) -> list:  # Soft pop everything (LIFO order)
        return list(reversed(self.stack))

    def is_empty(self):
        return len(self.stack) == 0

    def size(self):
        return len(self.stack)

    def clear(self):
        self.stack.clear()

if __name__ == "__main__":
    asyncio.run(send_command_to_device("30", "TEST_RESULTS"))
    data = {
        "type": "Test",
        "Test#": "C5627272",
        "Result": "Positive",
        "Level": "10-15pbb",
        "Purity":"N/A",
        "Type":"Maize",
        "Count": "200",
        
    }
    
    ordered_keys = ["Test#", "Result","Level","Purity","Type","Count"]
    filtered_data = dict_to_ordered_key_value_list(data,ordered_keys)
    f=LIFOStorage(3)
    f.push(filtered_data)
    data["Level"]="100-200pbb"
    data["Test#"]="XDLS899"
    data["Count"]="800"
    filtered_data = dict_to_ordered_key_value_list(data,ordered_keys)
    f.push(filtered_data)
    for x in f.peek_all():
        print(x)

 