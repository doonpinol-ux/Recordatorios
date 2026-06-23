import tkinter as tk
import json
import os
import sys
import threading
import winreg
from tkcalendar import Calendar
from tkinter import messagebox
from datetime import datetime
from PIL import Image, ImageDraw
import pystray

DATA_FILE = "recordatorios.json"

def load_reminders():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("recordatorios", []), data.get("tema", "claro")
    return [], "claro"

def save_reminders(tema):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"recordatorios": REMINDERS, "tema": tema}, f, ensure_ascii=False, indent=4)

REMINDERS, TEMA_GUARDADO = load_reminders()

class ReminderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Recordatorios")
        self.geometry("500x600")
        self.resizable(False, True)
        self.configure(bg="#f5f5f0")
        self.expanded = {}
        self.reminders_shown = []
        self.panel_open = False
        self.tema_actual = TEMA_GUARDADO
        self.temas = {
            "claro": {
                "bg_principal": "#F5F5F0",
                "bg_superficie": "#FFFFFF",
                "bg_tarjeta": "#E8E8E2",
                "bg_header": "#FFFFFF",
                "texto_principal": "#1A1A1A",
                "texto_secundario": "#888880",
            },
            "gris": {
                "bg_principal": "#E8E8E8",
                "bg_superficie": "#F0F0F0",
                "bg_tarjeta": "#DCDCDC",
                "bg_header": "#F0F0F0",
                "texto_principal": "#2C2C2C",
                "texto_secundario": "#666660",
            },
            "oscuro": {
                "bg_principal": "#121212",
                "bg_superficie": "#1E1E1E",
                "bg_tarjeta": "#2A2A2A",
                "bg_header": "#1E1E1E",
                "texto_principal": "#F5F5F5",
                "texto_secundario": "#E0E0E0",
            }
        }
        self.build_ui()
        self._startup_time = datetime.now()
        self.check_reminders()
        self.protocol("WM_DELETE_WINDOW", self.hide_window)
        self.after(0, self.create_tray_icon)

    def build_ui(self):
        t = self.temas[self.tema_actual]

        self.header_frame = tk.Frame(self, bg="#ffffff", pady=12)
        self.header_frame.pack(fill="x")

        self.header_label = tk.Label(self.header_frame, text="🔔 Recordatorios",
                                     font=("Arial", 16, "bold"), bg="#ffffff", fg="#1a1a1a")
        self.header_label.pack(side="left", padx=20)

        self.settings_btn = tk.Button(self.header_frame, text="⚙️",
                                      font=("Arial", 14), bg="#ffffff",
                                      relief="flat", cursor="hand2",
                                      command=self.toggle_panel)
        self.settings_btn.pack(side="right", padx=20)

        self.stats_frame = tk.Frame(self, bg="#f5f5f0", pady=10)
        self.stats_frame.pack(fill="x", padx=20)

        self.total_card = tk.Frame(self.stats_frame, bg="#e8e8e2", padx=16, pady=10)
        self.total_card.pack(side="left", expand=True, fill="x", padx=(0, 6))
        self.total_label_title = tk.Label(self.total_card, text="Total",
                                          font=("Arial", 11), bg="#e8e8e2", fg="#666660")
        self.total_label_title.pack(anchor="w")
        self.total_label_value = tk.Label(self.total_card, text=str(len(REMINDERS)),
                                          font=("Arial", 22, "bold"), bg="#e8e8e2", fg="#1a1a1a")
        self.total_label_value.pack(anchor="w")

        self.next_card = tk.Frame(self.stats_frame, bg="#e8e8e2", padx=16, pady=10)
        self.next_card.pack(side="left", expand=True, fill="x", padx=(6, 0))
        self.next_label_title = tk.Label(self.next_card, text="Próximo",
                                         font=("Arial", 11), bg="#e8e8e2", fg="#666660")
        self.next_label_title.pack(anchor="w")
        self.next_label_value = tk.Label(self.next_card,
                                         text=min(REMINDERS, key=lambda r: datetime.strptime(r["datetime"], "%d/%m/%Y, %I:%M %p"))["datetime"] if REMINDERS else "Sin recordatorios",
                                         font=("Arial", 12, "bold"), bg="#e8e8e2", fg="#1a1a1a")
        self.next_label_value.pack(anchor="w")

        self.add_btn = tk.Button(self, text="+ Agregar recordatorio",
                                 font=("Arial", 12), bg="#dbeafe", fg="#1e40af",
                                 relief="flat", cursor="hand2", pady=8,
                                 command=self.open_add_window)
        self.add_btn.pack(fill="x", padx=20, pady=(0, 12))

        self.proximos_label = tk.Label(self, text="PRÓXIMOS",
                                       font=("Arial", 10, "bold"), bg="#f5f5f0", fg="#888880")
        self.proximos_label.pack(anchor="w", padx=20, pady=(0, 6))

        self.list_frame = tk.Frame(self, bg="#f5f5f0")
        self.list_frame.pack(fill="both", expand=True, padx=20)

        self.render_list()

        self.settings_panel = tk.Frame(self, bg="#e8e8e2", width=220)
        self.settings_panel.place(x=-220, y=0, relheight=1)
        self.settings_panel.pack_propagate(False)
        self.settings_panel.lift()

        self.settings_title_label = tk.Label(self.settings_panel, text="Configuración",
                                             font=("Arial", 13, "bold"), bg="#e8e8e2", fg="#1a1a1a")
        self.settings_title_label.pack(anchor="w", padx=16, pady=(20, 16))

        self.settings_tema_label = tk.Label(self.settings_panel, text="TEMA",
                                            font=("Arial", 10, "bold"), bg="#e8e8e2", fg="#888880")
        self.settings_tema_label.pack(anchor="w", padx=16, pady=(0, 8))

        self.tema_buttons = []
        for nombre, funcion in [("Claro", self.tema_claro), ("Gris", self.tema_gris), ("Oscuro", self.tema_oscuro)]:
            btn = tk.Button(self.settings_panel, text=nombre,
                            font=("Arial", 11), bg="#ffffff",
                            fg="#1a1a1a", relief="flat", cursor="hand2",
                            anchor="w", padx=12, pady=6,
                            command=funcion)
            btn.pack(fill="x", padx=16, pady=2)
            self.tema_buttons.append(btn)

        tk.Frame(self.settings_panel, bg=t["bg_tarjeta"], height=1).pack(fill="x", padx=16, pady=(12, 8))

        self.autostart_btn = tk.Button(self.settings_panel, text="Inicio automático: OFF",
                                       font=("Arial", 11), relief="flat", cursor="hand2",
                                       anchor="w", padx=12, pady=6,
                                       command=self.toggle_autostart)
        self.autostart_btn.pack(fill="x", padx=16, pady=2)

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r"Software\Microsoft\Windows\CurrentVersion\Run",
                                 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, "Kahatsa")
            winreg.CloseKey(key)
            self.autostart_btn.config(text="Inicio automático: ON")
        except FileNotFoundError:
            self.autostart_btn.config(text="Inicio automático: OFF")

        self.apply_theme(self.tema_actual)

    def render_list(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        for i, reminder in enumerate(REMINDERS):
            self.build_reminder_card(i, reminder)

    def build_reminder_card(self, index, reminder):
        t = self.temas[self.tema_actual]
        is_expanded = self.expanded.get(index, False)

        card = tk.Frame(self.list_frame, bg=t["bg_superficie"],
                        highlightbackground="#ddddda", highlightthickness=1)
        card.pack(fill="x", pady=4)

        header_bg = t["bg_tarjeta"] if is_expanded else t["bg_superficie"]
        header = tk.Frame(card, bg=header_bg, cursor="hand2")
        header.pack(fill="x")

        left = tk.Frame(header, bg=header_bg)
        left.pack(side="left", padx=12, pady=10)
        tk.Label(left, text=reminder["title"], font=("Arial", 13, "bold"),
                 bg=header_bg, fg=t["texto_principal"]).pack(anchor="w")
        tk.Label(left, text=reminder["datetime"], font=("Arial", 11),
                 bg=header_bg, fg=t["texto_secundario"]).pack(anchor="w")

        right = tk.Frame(header, bg=header_bg)
        right.pack(side="right", padx=12)

        arrow = "▲" if is_expanded else "▼"
        trash_btn = tk.Button(right, text="🗑", font=("Arial", 13), bg=header_bg,
                              fg=t["texto_secundario"], relief="flat", cursor="hand2",
                              bd=0, highlightthickness=0,
                              command=lambda i=index: self.delete_reminder(i))
        trash_btn.pack(side="left", padx=(0, 8))

        tk.Label(right, text=arrow, font=("Arial", 11), bg=header_bg,
                 fg=t["texto_secundario"]).pack(side="left")

        for widget in [header, left, right]:
            widget.bind("<Button-1>", lambda e, i=index: self.toggle(i))
        for child in left.winfo_children():
            child.bind("<Button-1>", lambda e, i=index: self.toggle(i))
        for child in right.winfo_children():
            if child != trash_btn:
                child.bind("<Button-1>", lambda e, i=index: self.toggle(i))

        if is_expanded:
            separator = tk.Frame(card, bg="#ddddda", height=1)
            separator.pack(fill="x")
            desc = tk.Label(card, text=reminder["description"],
                            font=("Arial", 11), bg=t["bg_superficie"],
                            fg=t["texto_secundario"],
                            wraplength=420, justify="left", padx=12, pady=10)
            desc.pack(anchor="w")

    def toggle(self, index):
        self.expanded[index] = not self.expanded.get(index, False)
        self.render_list()

    def delete_reminder(self, index):
        reminder = REMINDERS[index]
        confirm = messagebox.askyesno(
            "Eliminar recordatorio",
            f"¿Eliminar '{reminder['title']}'?"
        )
        if confirm:
            reminder_id = f"{reminder['title']}|{reminder['datetime']}"
            self.reminders_shown = [r for r in self.reminders_shown if r != reminder_id]
            REMINDERS.pop(index)
            self.expanded.pop(index, None)
            save_reminders(self.tema_actual)
            self.render_list()
            self.update_stats()

    def open_add_window(self):
        t = self.temas[self.tema_actual]

        win = tk.Toplevel(self)
        win.title("Nuevo recordatorio")
        win.geometry("400x690")
        win.resizable(False, False)
        win.configure(bg=t["bg_principal"])
        win.grab_set()

        tk.Label(win, text="Fecha", font=("Arial", 11, "bold"),
                 bg=t["bg_principal"], fg=t["texto_principal"]).pack(anchor="w", padx=20, pady=(20, 4))

        cal = Calendar(win, selectmode="day", date_pattern="dd/mm/yyyy",
                       font=("Arial", 10), background=t["bg_superficie"],
                       foreground=t["texto_principal"], headersbackground="#dbeafe",
                       headersforeground="#1e40af", selectbackground="#1e40af")
        cal.pack(padx=20, fill="x")

        tk.Label(win, text="Hora", font=("Arial", 11, "bold"),
                 bg=t["bg_principal"], fg=t["texto_principal"]).pack(anchor="w", padx=20, pady=(16, 4))

        time_frame = tk.Frame(win, bg=t["bg_principal"])
        time_frame.pack(anchor="w", padx=20)

        hour_var = tk.StringVar(value="12")
        minute_var = tk.StringVar(value="00")
        ampm_var = tk.StringVar(value="AM")

        def validate_hour(*args):
            val = hour_var.get()
            if val.isdigit():
                n = int(val)
                if n < 1:
                    hour_var.set("01")
                elif n > 12:
                    hour_var.set("12")

        def validate_minute(*args):
            val = minute_var.get()
            if val.isdigit():
                n = int(val)
                if n < 0:
                    minute_var.set("00")
                elif n > 59:
                    minute_var.set("59")

        hour_var.trace_add("write", validate_hour)
        minute_var.trace_add("write", validate_minute)

        tk.Spinbox(time_frame, from_=1, to=12, width=3, textvariable=hour_var,
                   format="%02.0f", font=("Arial", 12),
                   bg=t["bg_superficie"], fg=t["texto_principal"],
                   buttonbackground=t["bg_tarjeta"]).pack(side="left")
        tk.Label(time_frame, text=":", font=("Arial", 14, "bold"),
                 bg=t["bg_principal"], fg=t["texto_principal"]).pack(side="left", padx=4)
        tk.Spinbox(time_frame, from_=0, to=59, width=3, textvariable=minute_var,
                   format="%02.0f", font=("Arial", 12),
                   bg=t["bg_superficie"], fg=t["texto_principal"],
                   buttonbackground=t["bg_tarjeta"]).pack(side="left")
        
        ampm_menu = tk.OptionMenu(time_frame, ampm_var, "AM", "PM")
        ampm_menu.configure(bg=t["bg_superficie"], fg=t["texto_principal"],
                            activebackground=t["bg_tarjeta"], activeforeground=t["texto_principal"],
                            relief="flat", highlightthickness=0)
        ampm_menu["menu"].configure(bg=t["bg_superficie"], fg=t["texto_principal"])
        ampm_menu.pack(side="left", padx=(8, 0))

        tk.Label(win, text="Título", font=("Arial", 11, "bold"),
                 bg=t["bg_principal"], fg=t["texto_principal"]).pack(anchor="w", padx=20, pady=(16, 4))

        title_entry = tk.Entry(win, font=("Arial", 12), relief="solid", bd=1,
                               bg=t["bg_superficie"], fg=t["texto_principal"],
                               insertbackground=t["texto_principal"])
        title_entry.pack(fill="x", padx=20)

        title_error = tk.Label(win, text="", font=("Arial", 10),
                               bg=t["bg_principal"], fg="#dc2626")
        title_error.pack(anchor="w", padx=20)

        tk.Label(win, text="Descripción", font=("Arial", 11, "bold"),
                 bg=t["bg_principal"], fg=t["texto_principal"]).pack(anchor="w", padx=20, pady=(8, 4))

        desc_entry = tk.Text(win, font=("Arial", 11), relief="solid", bd=1, height=4,
                             bg=t["bg_superficie"], fg=t["texto_principal"],
                             insertbackground=t["texto_principal"])
        desc_entry.pack(fill="x", padx=20)

        char_counter = tk.Label(win, text="0 / 150", font=("Arial", 9),
                                bg=t["bg_principal"], fg=t["texto_secundario"])
        char_counter.pack(anchor="e", padx=20)

        def on_desc_change(event=None):
            content = desc_entry.get("1.0", "end-1c")
            count = len(content)
            if count > 150:
                desc_entry.delete("1.0", "end")
                desc_entry.insert("1.0", content[:150])
                count = 150
            char_counter.config(text=f"{count} / 150",
                                fg="#dc2626" if count >= 140 else t["texto_secundario"])

        desc_entry.bind("<KeyRelease>", on_desc_change)

        def save():
            title = title_entry.get().strip()
            description = desc_entry.get("1.0", "end-1c").strip()

            if not title:
                title_error.config(text="El título es obligatorio.")
                title_entry.focus()
                return

            title_error.config(text="")

            hour = hour_var.get().zfill(2)
            minute = minute_var.get().zfill(2)
            ampm = ampm_var.get()
            date = cal.get_date()

            REMINDERS.append({
                "title": title,
                "datetime": f"{date}, {hour}:{minute} {ampm}",
                "description": description
            })

            save_reminders(self.tema_actual)
            self.render_list()
            self.update_stats()
            win.destroy()

        tk.Button(win, text="Guardar recordatorio", font=("Arial", 12),
                  bg="#1e40af", fg="#ffffff", relief="flat", cursor="hand2",
                  pady=8, command=save).pack(fill="x", padx=20, pady=(16, 0))

    def check_reminders(self):
        now = datetime.now()
        for reminder in REMINDERS:
            date_obj = datetime.strptime(reminder["datetime"], "%d/%m/%Y, %I:%M %p")
            reminder_id = f"{reminder['title']}|{reminder['datetime']}"
            if date_obj <= now and reminder_id not in self.reminders_shown:
                self.show_reminder(reminder, vencido=date_obj < self._startup_time)
                self.reminders_shown.append(reminder_id)

        self.after(30000, self.check_reminders)

    def show_reminder(self, reminder, vencido=False):
        t = self.temas[self.tema_actual]

        win = tk.Toplevel(self)
        win.attributes("-fullscreen", True)
        win.attributes("-topmost", True)
        win.protocol("WM_DELETE_WINDOW", lambda: None)
        win.configure(bg=t["bg_principal"])

        center = tk.Frame(win, bg=t["bg_principal"])
        center.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(center, text="🔔", font=("Arial", 48),
                 bg=t["bg_principal"]).pack(pady=(0, 16))

        if vencido:
            tk.Label(center, text="Recordatorio perdido",
                     font=("Arial", 12, "bold"), bg=t["bg_principal"],
                     fg="#dc2626").pack(pady=(0, 6))

        tk.Label(center, text=reminder["title"],
                 font=("Arial", 28, "bold"),
                 bg=t["bg_principal"], fg=t["texto_principal"],
                 wraplength=600, justify="center").pack(pady=(0, 12))

        if reminder.get("description", "").strip():
            tk.Label(center, text=reminder["description"],
                     font=("Arial", 14),
                     bg=t["bg_principal"], fg=t["texto_secundario"],
                     wraplength=500, justify="center").pack(pady=(0, 40))
        else:
            tk.Frame(center, bg=t["bg_principal"], height=40).pack()

        close_btn = tk.Button(center, text="Cerrar (5)",
                              font=("Arial", 13), width=20,
                              bg=t["bg_tarjeta"], fg=t["texto_secundario"],
                              relief="flat", cursor="hand2",
                              state="disabled", pady=10,
                              command=win.destroy)
        close_btn.pack()

        def countdown(seconds):
            if seconds > 0:
                close_btn.config(text=f"Cerrar ({seconds})")
                win.after(1000, countdown, seconds - 1)
            else:
                close_btn.config(
                    text="Cerrar",
                    state="normal",
                    bg="#1e40af",
                    fg="#ffffff",
                    cursor="hand2"
                )

        countdown(5)

    def apply_theme(self, nombre_tema):
        self.tema_actual = nombre_tema
        t = self.temas[nombre_tema]

        self.configure(bg=t["bg_principal"])

        self.header_frame.configure(bg=t["bg_header"])
        self.header_label.configure(bg=t["bg_header"], fg=t["texto_principal"])
        self.settings_btn.configure(bg=t["bg_header"])

        self.stats_frame.configure(bg=t["bg_principal"])
        self.total_card.configure(bg=t["bg_tarjeta"])
        self.total_label_title.configure(bg=t["bg_tarjeta"], fg=t["texto_secundario"])
        self.total_label_value.configure(bg=t["bg_tarjeta"], fg=t["texto_principal"])
        self.next_card.configure(bg=t["bg_tarjeta"])
        self.next_label_title.configure(bg=t["bg_tarjeta"], fg=t["texto_secundario"])
        self.next_label_value.configure(bg=t["bg_tarjeta"], fg=t["texto_principal"])

        self.add_btn.configure(bg="#dbeafe", fg="#1e40af")

        self.proximos_label.configure(bg=t["bg_principal"], fg=t["texto_secundario"])

        self.list_frame.configure(bg=t["bg_principal"])

        self.settings_panel.configure(bg=t["bg_tarjeta"])
        self.settings_title_label.configure(bg=t["bg_tarjeta"], fg=t["texto_principal"])
        self.settings_tema_label.configure(bg=t["bg_tarjeta"], fg=t["texto_secundario"])
        for btn in self.tema_buttons:
            btn.configure(bg=t["bg_superficie"], fg=t["texto_principal"])

        save_reminders(self.tema_actual)
        self.render_list()

    def tema_claro(self):
        self.apply_theme("claro")

    def tema_gris(self):
        self.apply_theme("gris")

    def tema_oscuro(self):
        self.apply_theme("oscuro")

    def toggle_panel(self):
        if self.panel_open:
            self.slide_panel(target=-220)
        else:
            self.slide_panel(target=0)
        self.panel_open = not self.panel_open

    def slide_panel(self, target):
        current = self.settings_panel.winfo_x()
        step = 20 if target > current else -20

        if (step > 0 and current < target) or (step < 0 and current > target):
            self.settings_panel.place(x=current + step, y=0, relheight=1)
            self.after(10, lambda: self.slide_panel(target))
        else:
            self.settings_panel.place(x=target, y=0, relheight=1)

    def update_stats(self):
        self.total_label_value.configure(text=str(len(REMINDERS)))

        if REMINDERS:
            proximo = min(REMINDERS, key=lambda r: datetime.strptime(r["datetime"], "%d/%m/%Y, %I:%M %p"))
            self.next_label_value.configure(text=proximo["datetime"])
        else:
            self.next_label_value.configure(text="Sin recordatorios")

    def create_tray_icon(self):
        image = Image.new("RGB", (64, 64), color="#1e40af")
        draw = ImageDraw.Draw(image)
        draw.ellipse([16, 16, 48, 48], fill="#ffffff")

        menu = pystray.Menu(
            pystray.MenuItem("Abrir", self.show_window, default=True),
            pystray.MenuItem("Salir", self.quit_app)
        )

        self.tray_icon = pystray.Icon("Kahatsa", image, "Kahatsa", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_window(self):
        self.after(0, self.deiconify)
        self.after(0, self.lift)

    def quit_app(self):
        self.tray_icon.stop()
        self.destroy()

    def hide_window(self):
        self.withdraw()
        if not hasattr(self, "tray_icon"):
            self.create_tray_icon()

    def toggle_autostart(self):
        app_name = "Kahatsa"
        script_path = os.path.abspath(sys.argv[0])
        python_path = sys.executable
        command = f'"{python_path}" "{script_path}"'
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run",
                             0, winreg.KEY_ALL_ACCESS)
        try:
            winreg.QueryValueEx(key, app_name)
            winreg.DeleteValue(key, app_name)
            self.autostart_btn.config(text="Inicio automático: OFF")
        except FileNotFoundError:
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, command)
            self.autostart_btn.config(text="Inicio automático: ON")
        finally:
            winreg.CloseKey(key)

root = ReminderApp()
root.mainloop()


      ⢰⡿⠋⠁⠀⠀⠈⠉⠙⠻⣷⣄⠀⠀⠀⠀⠀ ⠀⠀⠀⠀
     ⢀⣿⠇⠀⢀⣴⣶⡾⠿⠿⠿⢿⣿⣦⡀
⠀⠀⣀⣀⣸⡿⠀⠀⢸⣿⣇⠀⠀⠀⠀⠀⠀ ⠙⣷⡀
⠀⣾⡟⠛⣿⡇⠀⠀⢸⣿⣿⣷⣤⣤⣤⣤⣶⣶⣿⠇⠀⠀⠀⠀⠀⠀⠀⣀⠀⠀ 
⢀⣿⠀⢀⣿⡇⠀⠀⠀⠻⢿⣿⣿⣿⣿⣿⠿⣿⡏⠀⠀⠀⠀⢴⣶⣶⣿⣿⣿⣆
⢸⣿⠀⢸⣿⡇⠀⠀⠀⠀⠀⠈⠉⠁⠀⠀⠀⣿⡇⣀⣠⣴⣾⣮⣝⠿⠿⠿⣻⡟
⢸⣿⠀⠘⣿⡇⠀⠀⠀⠀⠀⠀⠀⣠⣶⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠁⠉⠀
⠸⣿⠀⠀⣿⡇⠀⠀⠀⠀⠀⣠⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠟⠉⠀⠀⠀⠀
⠀⠻⣷⣶⣿⣇⠀⠀⠀⢠⣼⣿⣿⣿⣿⣿⣿⣿⣛⣛⣻⠉⠁⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⢸⣿⠀⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⢸⣿⣀⣀⣀⣼⡿⢿⣿⣿⣿⣿⣿⡿⣿⣿⡿⠀⠀⠀⠀⠀⠀⠀⠀⠀ ⠀⠀⠀⠀⠀
       ⠙⠛⠛⠛⠋⠁⠀⠙⠻⠿⠟⠋⠑⠛⠋
# Hecho con amor, by: "Zapoide".
