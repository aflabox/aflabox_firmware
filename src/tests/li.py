import socket

def listen_for_internet_status(port=5001):
    """ Listens for internet status messages from InternetQualityMonitor. """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", port))
        print(f"Listening for internet status updates on port {port}...")

        while True:
            data, addr = sock.recvfrom(1024)  # Buffer size is 1024 bytes
            message = data.decode()
            print(f"Received message: {message}")

if __name__ == "__main__":
    listen_for_internet_status()
