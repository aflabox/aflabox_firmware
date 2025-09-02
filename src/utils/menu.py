
class MenuContext:
    def __init__(self):
        self.items = [
            "Take Photo",
            "Account Balance",
            "Night Mode",
            "Day Mode"
        ]
        self.current_index = 0
        self.is_active = False
        self.button_press_start = 0
        self.LONG_PRESS_TIME = 1.0  # seconds for long press

    def start_menu(self):
        self.is_active = True
        self.current_index = 0

    def end_menu(self):
        self.is_active = False
        self.current_index = 0

    def next_item(self):
        self.current_index = (self.current_index + 1) % len(self.items)
        return self.get_current_item()

    def get_current_item(self):
        return self.items[self.current_index]