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
