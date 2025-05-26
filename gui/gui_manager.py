import tkinter as tk
from tkinter import messagebox


class GUIManager:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("AI 助手")

    def display_message(self, message):
        messagebox.showinfo("AI 助手", message)

    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    gui = GUIManager()
    gui.display_message("欢迎使用您的私人 AI 助手！")
    gui.run()
