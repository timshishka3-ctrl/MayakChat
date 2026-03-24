import json
import requests
from kivy.clock import Clock
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import ScreenManager, Screen
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.list import MDList, TwoLineListItem
from kivymd.uix.textfield import MDTextField
from kivymd.uix.toolbar import MDTopAppBar

BASE_URL = "https://mayakchat-2db67-default-rtdb.firebaseio.com/"


class LoginScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        layout = MDBoxLayout(orientation='vertical', padding=40, spacing=20, md_bg_color=[0, 0, 0, 1])
        self.toolbar = MDTopAppBar(title="ВХОД В МАЯК", md_bg_color=[0.2, 0, 0, 1])

        self.username = MDTextField(hint_text="Логин", mode="round")
        self.password = MDTextField(hint_text="Пароль", mode="round", password=True)

        btn = MDRaisedButton(text="ПОДКЛЮЧИТЬСЯ", md_bg_color=[0.7, 0, 0, 1],
                             pos_hint={"center_x": .5}, on_release=self.login)

        layout.add_widget(self.toolbar)
        layout.add_widget(self.username)
        layout.add_widget(self.password)
        layout.add_widget(btn)
        self.add_widget(layout)

    def login(self, *args):
        user = self.username.text.strip()
        pw = self.password.text.strip()
        if user and pw:
            try:
                # Простая проверка пароля в базе
                res = requests.get(f"{BASE_URL}users/{user}.json", timeout=3).json()
                if res:
                    if res['password'] == pw:
                        self.proceed(user)
                    else:
                        self.password.error = True
                        self.password.helper_text = "Неверный пароль!"
                else:
                    # Регистрация нового юзера
                    requests.put(f"{BASE_URL}users/{user}.json", data=json.dumps({"password": pw}), timeout=3)
                    self.proceed(user)
            except:
                print("Ошибка сети при логине")

    def proceed(self, user):
        MDApp.get_running_app().user_name = user
        self.manager.current = "chat_list"


class ChatListScreen(Screen):
    def on_enter(self):
        self.load_chats()
        Clock.schedule_interval(self.load_chats, 5)

    def on_leave(self):
        Clock.unschedule(self.load_chats)

    def __init__(self, **kw):
        super().__init__(**kw)
        layout = MDBoxLayout(orientation='vertical', md_bg_color=[0, 0, 0, 1])
        self.toolbar = MDTopAppBar(title="СПИСОК ЧАТОВ", md_bg_color=[0.3, 0, 0, 1])

        self.scroll = ScrollView()
        self.list = MDList()
        self.scroll.add_widget(self.list)

        add_layout = MDBoxLayout(adaptive_height=True, padding=10, spacing=10)
        self.new_chat = MDTextField(hint_text="Название чата", mode="rectangle")
        add_btn = MDRaisedButton(text="СОЗДАТЬ", on_release=self.create_chat)
        add_layout.add_widget(self.new_chat)
        add_layout.add_widget(add_btn)

        layout.add_widget(self.toolbar)
        layout.add_widget(self.scroll)
        layout.add_widget(add_layout)
        self.add_widget(layout)

    def load_chats(self, *args):
        try:
            res = requests.get(f"{BASE_URL}chats.json", timeout=2).json()
            if res:
                self.list.clear_widgets()
                for c_id in res.keys():
                    m_count = len(res[c_id].get('msgs', {}))
                    self.list.add_widget(TwoLineListItem(
                        text=f"Чат: {c_id}",
                        secondary_text=f"Сообщений: {m_count}",
                        on_release=self.open_chat))
        except:
            pass

    def create_chat(self, *args):
        c_id = self.new_chat.text.strip()
        if c_id:
            requests.patch(f"{BASE_URL}chats/{c_id}.json", data=json.dumps({"status": "active"}), timeout=2)
            self.new_chat.text = ""
            self.load_chats()

    def open_chat(self, instance):
        MDApp.get_running_app().chat_room = instance.text.replace("Чат: ", "")
        self.manager.current = "chat"


class ChatScreen(Screen):
    last_count = 0

    def on_enter(self):
        self.toolbar.title = f"Чат: {MDApp.get_running_app().chat_room}"
        self.last_count = 0
        self.chat_list.clear_widgets()
        Clock.schedule_interval(self.get_messages, 1)

    def on_leave(self):
        Clock.unschedule(self.get_messages)

    def __init__(self, **kw):
        super().__init__(**kw)
        layout = MDBoxLayout(orientation='vertical', md_bg_color=[0, 0, 0, 1])
        self.toolbar = MDTopAppBar(title="", md_bg_color=[0.5, 0, 0, 1],
                                   left_action_items=[["arrow-left", lambda x: self.back()]])
        self.scroll = ScrollView()
        self.chat_list = MDList()
        self.scroll.add_widget(self.chat_list)

        input_box = MDBoxLayout(padding=10, adaptive_height=True, spacing=10)
        self.msg = MDTextField(hint_text="Ваше сообщение...")
        btn = MDRaisedButton(text="ОТПР.", on_release=self.send_message)
        input_box.add_widget(self.msg)
        input_box.add_widget(btn)

        layout.add_widget(self.toolbar)
        layout.add_widget(self.scroll)
        layout.add_widget(input_box)
        self.add_widget(layout)

    def back(self):
        self.manager.current = "chat_list"

    def send_message(self, *args):
        app = MDApp.get_running_app()
        if self.msg.text:
            d = {"user": app.user_name, "text": self.msg.text}
            requests.post(f"{BASE_URL}chats/{app.chat_room}/msgs.json", data=json.dumps(d), timeout=2)
            self.msg.text = ""

    def get_messages(self, dt):
        app = MDApp.get_running_app()
        try:
            res = requests.get(f"{BASE_URL}chats/{app.chat_room}/msgs.json", timeout=1).json()
            if res and len(res) != self.last_count:
                self.chat_list.clear_widgets()
                for k in res:
                    m = res[k]
                    self.chat_list.add_widget(TwoLineListItem(text=m['user'], secondary_text=m['text']))
                self.last_count = len(res)
        except:
            pass


class MayakApp(MDApp):
    user_name = ""
    chat_room = ""

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Red"
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(ChatListScreen(name="chat_list"))
        sm.add_widget(ChatScreen(name="chat"))
        return sm


if __name__ == "__main__":
    MayakApp().run()