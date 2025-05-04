import tkinter as tk
from tkinter import messagebox, ttk
import json
import os
from datetime import datetime, timedelta
import uuid
import sys
import math
import calendar
import pystray
from PIL import Image
import threading

try:
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

class HabitTrackerApp:
    def __init__(self, root=None):
        self.today = datetime.now().date().isoformat()
        self.habits_data = self.load_habits()
        self.each_time_habits = self.habits_data.get('each_time_habits', [])
        self.daily_habits = self.habits_data.get('daily_habits', [])
        self.increment_mode = 'same_day'
        self.root = root
        self.current_habit = None
        self.icon = None  # For the system tray icon

        if root:
            self.root.title("Habit Tracker")
            self.root.geometry("400x500")
            self.root.configure(bg="#F3F4F6")
            self.setup_gui()
            self.render_habits()
            # Set up system tray on window close
            self.root.protocol('WM_DELETE_WINDOW', self.hide_window)
        else:
            self.run_console_mode()

    def setup_gui(self):
        """Set up the main GUI window with frames, buttons, and a scrollable canvas."""
        self.main_frame = tk.Frame(self.root, bg="#F3F4F6")
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.header_frame = tk.Frame(self.main_frame, bg="#4B5EAA")
        self.header_frame.pack(fill="x")
        self.header_label = tk.Label(
            self.header_frame, text="Habit Tracker - Daily Mode",
            font=("Arial", 16, "bold"), fg="white", bg="#4B5EAA", pady=10
        )
        self.header_label.pack()

        top_frame = tk.Frame(self.main_frame, bg="#F3F4F6")
        top_frame.pack(fill="x")

        self.mode_button = tk.Button(
            top_frame, text="Switch", command=self.toggle_increment_mode,
            bg="#4B5EAA", fg="white", font=("Arial", 10, "bold")
        )
        self.mode_button.pack(side="left", padx=5)

        input_frame = tk.Frame(top_frame, bg="#F3F4F6")
        input_frame.pack(side="right")

        self.habit_input = ttk.Entry(input_frame, width=15)
        self.habit_input.pack(side="left", padx=5)
        self.habit_input.bind("<Return>", lambda e: self.add_habit())

        tk.Button(
            input_frame, text="Add", command=self.add_habit,
            bg="#3B82F6", fg="white", font=("Arial", 10, "bold")
        ).pack(side="left", padx=5)

        self.canvas = tk.Canvas(self.main_frame, bg="#F3F4F6")
        self.scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#F3F4F6")

        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(fill="both", expand=True, pady=(5, 0))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        tk.Button(
            self.main_frame, text="View Stats", command=self.open_stats_window,
            bg="#8B5CF6", fg="white", font=("Arial", 10, "bold")
        ).pack(pady=5)

    def toggle_increment_mode(self):
        """Toggle between 'Daily' and 'Each Time' modes."""
        try:
            self.increment_mode = 'each_time' if self.increment_mode == 'same_day' else 'same_day'
            print(f"Switched to mode: {self.increment_mode}")
            if self.root:
                mode_text = "Daily" if self.increment_mode == 'same_day' else "Each Time"
                mode_color = "#4B5EAA" if self.increment_mode == 'same_day' else "#14B8A6"
                self.header_label.configure(text=f"Habit Tracker - {mode_text} Mode", bg=mode_color)
                self.header_frame.configure(bg=mode_color)
                self.mode_button.configure(bg=mode_color)
                self.render_habits()
                self.root.update()
        except Exception as e:
            print(f"Error toggling mode: {e}")
            if self.root:
                messagebox.showerror("Error", "Failed to toggle mode")

    def render_habits(self):
        """Render the list of habits in the scrollable frame."""
        try:
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()

            habits = self.each_time_habits if self.increment_mode == 'each_time' else self.daily_habits
            for habit in habits:
                frame = tk.Frame(self.scrollable_frame, bg="white", bd=2, highlightthickness=0)
                frame.pack(fill="x", pady=5, padx=5)

                frame.grid_columnconfigure(0, weight=1)

                tk.Label(frame, text="", bg="white").grid(row=0, column=0)

                habit_area = tk.Frame(frame, bg="white")
                habit_area.grid(row=0, column=1, sticky="e", padx=5)

                label = tk.Label(
                    habit_area, text=habit["text"], font=("Arial", 10), bg="white",
                    fg="gray" if habit["completed"] and self.increment_mode == 'same_day' else "black",
                    wraplength=200, anchor="w", padx=10, pady=5
                )
                label.pack(side="left")

                button_frame = tk.Frame(habit_area, bg="white")
                button_frame.pack(side="left", padx=5)

                text = "Complete" if not (self.increment_mode == 'same_day' and habit["completed"]) else "✔"
                bg = "#10B981" if text == "Complete" else "#FBBF24"
                tk.Button(
                    button_frame, text=text, command=lambda id=habit["id"]: self.toggle_habit_completion(id),
                    bg=bg, fg="white", font=("Arial", 9, "bold")
                ).pack(side="left", padx=2)

                tk.Button(
                    button_frame, text="Delete", command=lambda id=habit["id"]: self.delete_habit(id),
                    bg="#EF4444", fg="white", font=("Arial", 9, "bold")
                ).pack(side="left", padx=2)

                print(f"Rendered habit area: {habit['text']}, habit name: left of buttons, habit area: right-aligned (grid column 1, sticky=e)")
        except Exception as e:
            print(f"Error rendering habits: {e}")
            if self.root:
                messagebox.showerror("Error", "Failed to render habits")

    def open_stats_window(self):
        """Open a new window to display habit completion stats."""
        try:
            stats_window = tk.Toplevel(self.root)
            stats_window.title("Habit Completion Stats")
            stats_window.geometry("400x500")
            stats_window.configure(bg="#F3F4F6")

            main_frame = tk.Frame(stats_window, bg="#F3F4F6")
            main_frame.pack(fill="both", expand=True, padx=10, pady=10)

            tk.Label(
                main_frame, text="Completion Stats", font=("Arial", 14, "bold"),
                fg="white", bg="#4B5EAA", pady=8
            ).pack(fill="x", pady=(0, 10))

            canvas = tk.Canvas(main_frame, bg="#F3F4F6")
            scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = tk.Frame(canvas, bg="#F3F4F6")

            scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.configure(yscrollcommand=self.scrollbar.set)
            scrollbar.pack(side="right", fill="y")
            canvas.pack(fill="both", expand=True)
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

            self.render_habit_stats(scrollable_frame, "Each Time Mode", self.each_time_habits, "#14B8A6")
            self.each_time_graph_frame = tk.Frame(scrollable_frame, bg="#F3F4F6")
            self.each_time_graph_frame.pack(fill="x", pady=(10, 10), padx=5)

            self.render_habit_stats(scrollable_frame, "Daily Mode", self.daily_habits, "#4B5EAA")
            self.daily_graph_frame = tk.Frame(scrollable_frame, bg="#F3F4F6")
            self.daily_graph_frame.pack(fill="x", pady=(10, 10), padx=5)

            print("Opened stats window successfully")
        except Exception as e:
            print(f"Error opening stats window: {e}")
            if self.root:
                messagebox.showerror("Error", "Failed to open stats window")

    def render_habit_stats(self, parent, mode_name, habits, color):
        """Render the list of habits and their completion stats in the stats window."""
        tk.Label(
            parent, text=mode_name, font=("Arial", 12, "bold"),
            fg=color, bg="#F3F4F6", anchor="w"
        ).pack(anchor="w", pady=(10, 5), padx=5)
        if not habits:
            tk.Label(
                parent, text=f"No habits in {mode_name}", font=("Arial", 10, "italic"),
                fg="gray", bg="#F3F4F6", anchor="w", padx=10
            ).pack(anchor="w")
        else:
            for habit in habits:
                frame = tk.Frame(parent, bg="white")
                frame.pack(fill="x", pady=2, padx=5)
                label = tk.Label(
                    frame, text=f"{habit['text']}: {habit['completionCount']} times",
                    font=("Arial", 10), bg="white", anchor="w", padx=10, pady=5, cursor="hand2"
                )
                label.pack(side="left")
                label.bind("<Button-1>", lambda e, h=habit: self.show_habit_graph(h, color))

    def show_habit_graph(self, habit, color):
        """Display the graph or completion view for the selected habit."""
        graph_frame = self.each_time_graph_frame if habit in self.each_time_habits else self.daily_graph_frame
        for widget in graph_frame.winfo_children():
            widget.destroy()
        self.create_completion_graph(graph_frame, habit, color)
        self.current_habit = habit

    def create_completion_graph(self, parent_frame, habit, color):
        """Create the appropriate graph or completion view for the habit."""
        if habit in self.daily_habits:
            self.create_completion_view(parent_frame, habit, color)
        else:
            # Bar graph for Each Time Mode
            date_counts = {date: habit.get('completionDates', []).count(date) for date in set(habit.get('completionDates', []))}

            today = datetime.now().date()
            days_since_monday = today.weekday()
            start_date = today - timedelta(days=days_since_monday)
            dates = [start_date + timedelta(days=x) for x in range(7)]
            date_strings = [d.isoformat() for d in dates]
            frequencies = [date_counts.get(date, 0) for date in date_strings]
            date_labels = [d.strftime("%a %m-%d") for d in dates]

            max_freq = max(frequencies, default=0)
            if max_freq == 0:
                y_ticks = [0, 1]
            elif max_freq <= 3:
                y_ticks = list(range(0, max_freq + 1, 1))
            else:
                step = max(1, math.ceil(max_freq / 3))
                y_ticks = list(range(0, max_freq + step, step))

            fig, ax = plt.subplots(figsize=(4, 2.5))
            ax.bar(range(len(frequencies)), frequencies, color=color)
            ax.set_xticks(range(len(date_labels)))
            ax.set_xticklabels(date_labels, rotation=45, ha="right", fontsize=8)
            ax.set_xlabel("Date", fontsize=8)
            ax.set_ylabel("Completions", fontsize=8)
            ax.set_yticks(y_ticks)
            ax.tick_params(axis='y', labelsize=8)
            plt.title(f"{habit['text']}", fontsize=10)
            plt.tight_layout()

            canvas = FigureCanvasTkAgg(fig, master=parent_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="x", pady=5)
            plt.close(fig)

    def create_completion_view(self, parent_frame, habit, color):
        """Display a list of dates for the current month with completion status."""
        # Get the current month and year
        today = datetime.now().date()
        year = today.year
        month = today.month
        today_day = today.day  # e.g., 3 for May 3, 2025

        # Get the number of days in the current month
        _, num_days = calendar.monthrange(year, month)
        month_name = calendar.month_name[month]

        # Get completion dates for the habit
        completion_dates = habit.get('completionDates', [])
        print(f"Completion dates for habit {habit['text']}: {completion_dates}")

        # Create a frame for the completion view
        completion_frame = tk.Frame(parent_frame, bg="#F3F4F6")
        completion_frame.pack(fill="x", pady=5)

        # Add the month and year title
        tk.Label(
            completion_frame, text=f"{month_name} {year}", font=("Arial", 10, "bold"),
            fg=color, bg="#F3F4F6"
        ).pack(anchor="w")

        # Create a grid to display dates and their completion status
        date_grid = tk.Frame(completion_frame, bg="#F3F4F6")
        date_grid.pack(fill="x")

        # Display each day of the month
        for day in range(1, num_days + 1):
            date_str = f"{year}-{month:02d}-{day:02d}"
            col = (day - 1) % 7  # 7 columns per row
            row = (day - 1) // 7

            # Create a frame for the date and its status
            day_frame = tk.Frame(date_grid, bg="white", borderwidth=1, relief="solid")
            day_frame.grid(row=row * 2, column=col, padx=2, pady=2)

            # Display the date
            tk.Label(
                day_frame, text=str(day), font=("Arial", 8),
                bg="white", fg="black", width=5
            ).pack()

            # Determine the status: tick (✅), wrong (❌), or white square (⬜)
            if date_str in completion_dates:
                # Habit was completed on this day
                tk.Label(
                    day_frame, text="✅", font=("Arial", 10),
                    bg="white", fg="green"
                ).pack()
            elif day < today_day:
                # Previous day, habit not completed
                tk.Label(
                    day_frame, text="❌", font=("Arial", 10),
                    bg="white", fg="red"
                ).pack()
            else:
                # Future day (day >= today_day), show white square
                tk.Label(
                    day_frame, text="⬜", font=("Arial", 10),
                    bg="white", fg="black"
                ).pack()

    def hide_window(self):
        """Hide the window and show it on the system tray."""
        self.root.withdraw()  # Hide the window
        # Create system tray icon if not already created
        if not self.icon:
            # Create an icon (you'll need an icon file, e.g., 'icon.ico')
            try:
                image = Image.open("icon.ico")
            except FileNotFoundError:
                # Fallback to a default icon if icon.ico is not found
                image = Image.new('RGB', (64, 64), color='blue')
            menu = (
                pystray.MenuItem("Show", self.show_window),
                pystray.MenuItem("Quit", self.quit_window)
            )
            self.icon = pystray.Icon("Habit Tracker", image, "Habit Tracker", menu)
            # Run the system tray icon in a separate thread
            tray_thread = threading.Thread(target=self.icon.run)
            tray_thread.daemon = True
            tray_thread.start()

    def show_window(self):
        """Show the window again from the system tray."""
        if self.icon:
            self.icon.stop()
            self.icon = None
        self.root.deiconify()

    def quit_window(self):
        """Quit the application completely from the system tray."""
        if self.icon:
            self.icon.stop()
            self.icon = None
        self.root.destroy()

    def load_habits(self):
        """Load habits from habits.json or return default empty data."""
        try:
            if os.path.exists("habits.json"):
                with open("habits.json", "r") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        habits = [
                            h for h in data
                            if isinstance(h, dict) and "id" in h and "text" in h
                        ]
                        for h in habits:
                            h.setdefault("completionCount", 0)
                            h.setdefault("completionDates", [])
                            if h.get("lastCompleted") != self.today:
                                h["completed"] = False
                                h["lastCompleted"] = None
                        return {'each_time_habits': [], 'daily_habits': habits}
                    else:
                        each_time = data.get('each_time_habits', [])
                        daily = data.get('daily_habits', [])
                        if not (isinstance(each_time, list) and isinstance(daily, list)):
                            raise ValueError("Invalid habits data")
                        for h in each_time + daily:
                            if not isinstance(h, dict) or "id" not in h or "text" not in h:
                                raise ValueError("Invalid habit entry")
                            h.setdefault("completionCount", 0)
                            h.setdefault("completionDates", [])
                            if h.get("lastCompleted") != self.today:
                                h["completed"] = False
                                h["lastCompleted"] = None
                        return {'each_time_habits': each_time, 'daily_habits': daily}
            return {'each_time_habits': [], 'daily_habits': []}
        except Exception as e:
            print(f"Error loading habits: {e}")
            return {'each_time_habits': [], 'daily_habits': []}

    def save_habits(self):
        """Save habits to habits.json."""
        try:
            data = {
                'each_time_habits': self.each_time_habits,
                'daily_habits': self.daily_habits
            }
            with open("habits.json", "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving habits: {e}")

    def add_habit(self, habit_text=None):
        """Add a new habit to the appropriate list (Daily or Each Time)."""
        try:
            if self.root and not habit_text:
                habit_text = self.habit_input.get().strip()
            if not habit_text:
                raise ValueError("Habit cannot be empty")
            new_habit = {
                "id": str(uuid.uuid4()),
                "text": habit_text,
                "completed": False,
                "lastCompleted": None,
                "completionCount": 0,
                "completionDates": []
            }
            if self.increment_mode == 'each_time':
                self.each_time_habits.append(new_habit)
            else:
                self.daily_habits.append(new_habit)
            self.save_habits()
            if self.root:
                self.habit_input.delete(0, tk.END)
                self.render_habits()
            else:
                print("Habit added")
        except Exception as e:
            print(f"Error adding habit: {e}")
            if self.root:
                messagebox.showerror("Error", "Failed to add habit")

    def toggle_habit_completion(self, habit_id):
        """Toggle the completion status of a habit."""
        try:
            habits = self.each_time_habits if self.increment_mode == 'each_time' else self.daily_habits
            for habit in habits:
                if habit["id"] == habit_id:
                    if self.increment_mode == 'each_time':
                        habit["completionCount"] += 1
                        habit["completionDates"].append(self.today)
                    else:
                        habit["completed"] = not habit["completed"]
                        if habit["completed"]:
                            habit["lastCompleted"] = self.today
                            if self.today not in habit["completionDates"]:
                                habit["completionCount"] += 1
                                habit["completionDates"].append(self.today)
                        else:
                            habit["lastCompleted"] = None
                            if self.today in habit["completionDates"]:
                                habit["completionCount"] -= 1
                                habit["completionDates"].remove(self.today)
                    break
            self.save_habits()
            if self.root:
                self.render_habits()
        except Exception as e:
            print(f"Error toggling completion: {e}")
            if self.root:
                messagebox.showerror("Error", "Failed to toggle completion")

    def delete_habit(self, habit_id):
        """Delete a habit from the list."""
        try:
            habits = self.each_time_habits if self.increment_mode == 'each_time' else self.daily_habits
            habits[:] = [h for h in habits if h["id"] != habit_id]
            self.save_habits()
            if self.root:
                self.render_habits()
        except Exception as e:
            print(f"Error deleting habit: {e}")
            if self.root:
                messagebox.showerror("Error", "Failed to delete habit")

    def run_console_mode(self):
        """Run the app in console mode if GUI is not available."""
        while True:
            print("\nHabit Tracker (Console Mode)")
            print("1. List habits")
            print("2. Add habit")
            print("3. Complete habit")
            print("4. Delete habit")
            print("5. View completion stats")
            print("6. Toggle increment mode")
            print("7. Exit")
            try:
                choice = input("Choose an option (1-7): ").strip()
            except (EOFError, KeyboardInterrupt):
                print("Exiting.")
                break

            habits = self.each_time_habits if self.increment_mode == 'each_time' else self.daily_habits
            if choice == "1":
                if not habits:
                    print("No habits found.")
                for i, h in enumerate(habits, 1):
                    status = "✔" if h["completed"] and self.increment_mode == 'same_day' else " "
                    print(f"{i}. {h['text']} [{status}]")
            elif choice == "2":
                try:
                    habit_text = input("Enter habit: ").strip()
                    self.add_habit(habit_text)
                except Exception:
                    print("Error adding habit.")
            elif choice == "3":
                if not habits:
                    print("No habits to complete.")
                else:
                    for i, h in enumerate(habits, 1):
                        print(f"{i}. {h['text']}")
                    try:
                        idx = int(input("Enter habit number: ")) - 1
                        if 0 <= idx < len(habits):
                            self.toggle_habit_completion(habits[idx]["id"])
                            print("Habit status updated.")
                        else:
                            print("Invalid number.")
                    except ValueError:
                        print("Invalid input.")
            elif choice == "4":
                if not habits:
                    print("No habits to delete.")
                else:
                    for i, h in enumerate(habits, 1):
                        print(f"{i}. {h['text']}")
                    try:
                        idx = int(input("Enter habit number: ")) - 1
                        if 0 <= idx < len(habits):
                            self.delete_habit(habits[idx]["id"])
                            print("Habit deleted.")
                        else:
                            print("Invalid number.")
                    except ValueError:
                        print("Invalid input.")
            elif choice == "5":
                print("\nHabit Completion Stats:")
                print("Each Time Mode:")
                if not self.each_time_habits:
                    print("  No habits")
                for i, h in enumerate(self.each_time_habits, 1):
                    print(f"  {i}. {h['text']}: {h['completionCount']} times")
                    dates = sorted(set(h.get('completionDates', [])))
                    if dates:
                        print(f"    Dates: {', '.join(dates)}")
                print("Daily Mode:")
                if not self.daily_habits:
                    print("  No habits")
                for i, h in enumerate(self.daily_habits, 1):
                    print(f"  {i}. {h['text']}: {h['completionCount']} times")
                    dates = sorted(set(h.get('completionDates', [])))
                    if dates:
                        print(f"    Dates: {', '.join(dates)}")
            elif choice == "6":
                self.toggle_increment_mode()
            elif choice == "7":
                print("Exiting.")
                break
            else:
                print("Invalid option.")

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = HabitTrackerApp(root)
        root.mainloop()
    except Exception as e:
        if "no display name" in str(e) or "DISPLAY" in str(e):
            print("No display available. Running in console mode.")
            app = HabitTrackerApp(None)
        else:
            print(f"Failed to start: {e}")