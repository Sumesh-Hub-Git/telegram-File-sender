import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import time
from datetime import datetime
import mimetypes
import os

# Telegram Bot API
import requests
from tkinterdnd2 import DND_FILES, TkinterDnD

class TelegramImageSender:
    def __init__(self, root):
        self.root = root
        self.root.title("Telegram File Sender")
        self.root.geometry("800x600")
        self.root.minsize(600, 500)
        
        # State variables
        self.selected_images = []
        self.processed_images = 0
        self.error_count = 0
        self.is_running = False
        self.is_paused = False
        self.stop_requested = False
        
        # Telegram bot credentials
        self.bot_token = tk.StringVar()
        self.chat_id = tk.StringVar()
        
        # Delay settings
        self.delay_value = tk.StringVar(value="1")
        self.delay_unit = tk.StringVar(value="seconds")
        
        # Drag and drop variables for treeview reordering
        self.drag_src_item = None
        self.drag_src_index = None
        
        # Create responsive layout
        self.create_responsive_layout()
        self.register_drop_target(self.root)
        
        # Log queue
        self.log_queue = queue.Queue()
        self.update_log_display()
    
    def create_responsive_layout(self):
        """Create responsive layout with canvas that fills width properly"""
        # Main container frame
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill="both", expand=True, padx=5, pady=5)
        self.register_drop_target(self.main_container)
        
        # Canvas with scrollbar
        self.canvas = tk.Canvas(self.main_container, highlightthickness=0)
        self.register_drop_target(self.canvas)
        scrollbar = ttk.Scrollbar(self.main_container, orient="vertical", command=self.canvas.yview)
        
        # Use tk.Frame instead of ttk.Frame for bg support
        self.scrollable_frame = tk.Frame(self.canvas)
        self.register_drop_target(self.scrollable_frame)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        # Create window that fills the canvas width
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, 
                                                        anchor="nw", width=780)
        
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Bind mouse wheel
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)
        
        # Bind resize to update canvas window width
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        # Pack
        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # Create all sections
        self.create_control_section()
        self.create_delay_section()
        self.create_select_file_section()
        self.create_image_caption_editor_section()
        self.create_progress_section()
        self.create_log_section()
        self.create_button_section()
    
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling"""
        if event.num == 4 or event.num == 5:
            scroll_amount = -1 if event.num == 4 else 1
            self.canvas.yview_scroll(scroll_amount, "units")
        else:
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def _on_canvas_configure(self, event):
        """Update canvas window width when canvas is resized to prevent compression"""
        new_width = max(event.width, 780)
        self.canvas.itemconfig(self.canvas_window, width=new_width)
    
    def create_control_section(self):
        """Create control section with bot token and chat ID"""
        control_frame = ttk.LabelFrame(self.scrollable_frame, text="Control Section", padding="15")
        control_frame.pack(fill="x", padx=20, pady=5)
        
        # Bot Token
        token_frame = ttk.Frame(control_frame)
        token_frame.pack(fill="x", pady=5)
        ttk.Label(token_frame, text="Bot Token:", width=15, anchor="w").pack(side="left")
        token_entry = ttk.Entry(token_frame, textvariable=self.bot_token)
        token_entry.pack(side="left", fill="x", expand=True, padx=10)
        
        # Chat ID
        chat_frame = ttk.Frame(control_frame)
        chat_frame.pack(fill="x", pady=5)
        ttk.Label(chat_frame, text="Chat ID:", width=15, anchor="w").pack(side="left")
        chat_entry = ttk.Entry(chat_frame, textvariable=self.chat_id)
        chat_entry.pack(side="left", fill="x", expand=True, padx=10)
    
    def create_delay_section(self):
        """Create delay settings section"""
        delay_frame = ttk.LabelFrame(self.scrollable_frame, text="Delay Settings", padding="15")
        delay_frame.pack(fill="x", padx=20, pady=5)
        
        # Delay value and unit
        delay_unit_frame = ttk.Frame(delay_frame)
        delay_unit_frame.pack(fill="x", pady=5)
        
        ttk.Label(delay_unit_frame, text="Delay between files:", width=22, anchor="w").pack(side="left")
        
        delay_entry_frame = ttk.Frame(delay_unit_frame)
        delay_entry_frame.pack(side="left", padx=10)
        
        delay_value_entry = ttk.Entry(delay_entry_frame, textvariable=self.delay_value, width=10)
        delay_value_entry.pack(side="left", padx=2)
        
        unit_combo = ttk.Combobox(delay_entry_frame, textvariable=self.delay_unit, width=12, state="readonly")
        unit_combo["values"] = ("seconds", "minutes")
        unit_combo.current(0)
        unit_combo.pack(side="left", padx=2)
        
        ttk.Label(delay_frame, text="⚠️ Recommended: 1-3 seconds to avoid rate limiting", 
                  foreground="orange", wraplength=700).pack(pady=5)
    
    def create_select_file_section(self):
        """Create file selection section with drag-and-drop support"""
        select_frame = ttk.LabelFrame(self.scrollable_frame, text="Select Files", padding="15")
        select_frame.pack(fill="x", padx=20, pady=5)
        self.register_drop_target(select_frame)
        
        self.select_btn = ttk.Button(select_frame, text="Select Files", command=self.select_files)
        self.select_btn.pack(pady=5)
        self.register_drop_target(self.select_btn)
        
        self.files_label = ttk.Label(select_frame, text="No files selected — drop files here or use Select Files", foreground="gray")
        self.files_label.pack(pady=5)
        self.register_drop_target(self.files_label)
        
        self.caption_label = ttk.Label(select_frame, 
                                       text="Edit captions and drag rows or use ↑↓ buttons to reorder files", 
                                       foreground="blue", wraplength=750)
        self.caption_label.pack(pady=5)
    
    def create_image_caption_editor_section(self):
        """Create file caption editor with drag-to-reorder capability."""
        editor_frame = ttk.LabelFrame(self.scrollable_frame, 
                                     text="File Caption Editor (Drag to Reorder, Double-click to Edit)", 
                                     padding="15")
        editor_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        columns = ("order", "filename", "caption")
        self.image_tree = ttk.Treeview(editor_frame, columns=columns, show="headings", height=8, selectmode="browse")
        
        self.image_tree.heading("order", text="Order")
        self.image_tree.heading("filename", text="File")
        self.image_tree.heading("caption", text="Caption")
        
        self.image_tree.column("order", width=60, anchor="center")
        self.image_tree.column("filename", width=220, anchor="w")
        self.image_tree.column("caption", width=400, anchor="w")
        
        scrollbar_y = ttk.Scrollbar(editor_frame, orient="vertical", command=self.image_tree.yview)
        scrollbar_x = ttk.Scrollbar(editor_frame, orient="horizontal", command=self.image_tree.xview)
        self.image_tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        self.register_drop_target(self.image_tree)
        
        scrollbar_y.pack(side="right", fill="y")
        scrollbar_x.pack(side="bottom", fill="x")
        self.image_tree.pack(fill="both", expand=True)
        
        # Bind events for drag and drop reordering
        self.image_tree.bind("<Button-1>", self.on_tree_click)
        self.image_tree.bind("<B1-Motion>", self.on_tree_drag)
        self.image_tree.bind("<ButtonRelease-1>", self.on_tree_release)
        
        # Bind selection event for editing
        self.image_tree.bind("<<TreeviewSelect>>", self.on_image_selected)
        
        # Bind double-click to edit caption
        self.image_tree.bind("<Double-1>", self.on_double_click)
        
        self.selection_info = tk.StringVar(value="Click and drag to reorder, or select and double-click to edit caption")
        selection_label = ttk.Label(editor_frame, textvariable=self.selection_info, foreground="gray")
        selection_label.pack(pady=5)
        
        edit_frame = ttk.Frame(editor_frame)
        edit_frame.pack(fill="x", pady=5)
        
        ttk.Label(edit_frame, text="Edit Caption:", width=15, anchor="w").pack(side="left")
        self.caption_entry = ttk.Entry(edit_frame, width=60)
        self.caption_entry.pack(side="left", fill="x", expand=True, padx=10)
        
        # Button row 1
        button_frame1 = ttk.Frame(editor_frame)
        button_frame1.pack(fill="x", pady=5)
        
        ttk.Button(button_frame1, text="↑ Move Up", command=self.move_up, width=14).pack(side="left", padx=5)
        ttk.Button(button_frame1, text="↓ Move Down", command=self.move_down, width=14).pack(side="left", padx=5)
        ttk.Button(button_frame1, text="⇄ Swap Next", command=self.swap_next, width=14).pack(side="left", padx=5)
        
        # Button row 2
        button_frame2 = ttk.Frame(editor_frame)
        button_frame2.pack(fill="x", pady=5)
        
        ttk.Button(button_frame2, text="✏️ Update Caption", command=self.update_caption, width=16).pack(side="left", padx=5)
        ttk.Button(button_frame2, text="🔄 Auto-Number", command=self.auto_number_captions, width=15).pack(side="left", padx=5)
        ttk.Button(button_frame2, text="🗑️ Remove", command=self.remove_selected, width=12).pack(side="left", padx=5)
    
    def create_progress_section(self):
        """Create progress and status bar section"""
        progress_frame = ttk.LabelFrame(self.scrollable_frame, text="Progress and Status", padding="15")
        progress_frame.pack(fill="x", padx=20, pady=5)
        
        stats_frame = ttk.Frame(progress_frame)
        stats_frame.pack(fill="x", pady=5)
        
        ttk.Label(stats_frame, text="Selected:", width=12, anchor="w").pack(side="left")
        self.selected_count_label = ttk.Label(stats_frame, text="0", foreground="blue")
        self.selected_count_label.pack(side="left", padx=15)
        
        ttk.Label(stats_frame, text="Processed:", width=12, anchor="w").pack(side="left", padx=30)
        self.processed_count_label = ttk.Label(stats_frame, text="0", foreground="green")
        self.processed_count_label.pack(side="left", padx=15)
        
        ttk.Label(stats_frame, text="Errors:", width=12, anchor="w").pack(side="left", padx=30)
        self.error_count_label = ttk.Label(stats_frame, text="0", foreground="red")
        self.error_count_label.pack(side="left", padx=15)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode="determinate")
        self.progress_bar.pack(fill="x", pady=10)
        
        self.progress_label = ttk.Label(progress_frame, text="0%")
        self.progress_label.pack()
    
    def create_log_section(self):
        """Create log section"""
        log_frame = ttk.LabelFrame(self.scrollable_frame, text="Log", padding="15")
        log_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        self.log_text = tk.Text(log_frame, height=6, wrap="word", state="disabled")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        self.log_text.pack(fill="both", expand=True)
    
    def create_button_section(self):
        """Create button section - always visible and centered"""
        button_frame = ttk.LabelFrame(self.scrollable_frame, text="Actions", padding="15")
        button_frame.pack(fill="x", padx=20, pady=10)
        
        button_inner = ttk.Frame(button_frame)
        button_inner.pack(expand=True)
        
        self.start_btn = ttk.Button(button_inner, text="Start", command=self.start_processing, width=15)
        self.start_btn.pack(side="left", padx=15, pady=5)
        
        self.stop_btn = ttk.Button(button_inner, text="Stop", command=self.stop_processing, width=15, state="disabled")
        self.stop_btn.pack(side="left", padx=15, pady=5)
        
        self.pause_btn = ttk.Button(button_inner, text="Pause", command=self.toggle_pause, width=15, state="disabled")
        self.pause_btn.pack(side="left", padx=15, pady=5)
    
    # Treeview Drag and Drop for Reordering
    def on_tree_click(self, event):
        """Handle treeview click for drag start"""
        if self.image_tree.identify_region(event.x, event.y) == "cell":
            item = self.image_tree.identify_row(event.y)
            if item:
                self.drag_src_item = item
                self.drag_src_index = int(self.image_tree.index(item))
                self.image_tree.selection_set(item)
    
    def on_tree_drag(self, event):
        """Handle treeview drag - visual feedback only"""
        if self.drag_src_item is None:
            return
        
        target_item = self.image_tree.identify_row(event.y)
        if target_item and target_item != self.drag_src_item:
            self.image_tree.selection_set(target_item)
            self.image_tree.see(target_item)
    
    def on_tree_release(self, event):
        """Handle treeview release - perform reorder"""
        if self.drag_src_item is None:
            return
        
        target_item = self.image_tree.identify_row(event.y)
        
        if self.drag_src_index is not None and self.selected_images:
            if target_item:
                insertion_index = int(self.image_tree.index(target_item))
                row = self.image_tree.bbox(target_item)
                if row and event.y >= row[1] + row[3] // 2:
                    insertion_index += 1
            else:
                insertion_index = 0 if event.y < 0 else len(self.selected_images)

            destination = insertion_index
            if self.drag_src_index < insertion_index:
                destination -= 1
            destination = max(0, min(destination, len(self.selected_images) - 1))
            if destination != self.drag_src_index:
                self.move_image_to(self.drag_src_index, destination)
        
        self.drag_src_item = None
        self.drag_src_index = None
    
    def move_image_to(self, src_index, dest_index):
        """Move image from src_index to dest_index"""
        if src_index < 0 or src_index >= len(self.selected_images):
            return
        if dest_index < 0 or dest_index >= len(self.selected_images):
            return
        
        # Get the item to move
        item = self.selected_images[src_index]
        
        # Remove from old position
        self.selected_images.pop(src_index)
        
        # Insert at new position
        self.selected_images.insert(dest_index, item)
        
        # Rebuild treeview
        self.rebuild_treeview()
        
        # Select the moved item
        items = self.image_tree.get_children()
        if dest_index < len(items):
            self.image_tree.selection_set(items[dest_index])
        
        self.log(f"Reordered file to position {dest_index + 1}")
    
    def select_files(self):
        """Open file dialog to select files"""
        files = filedialog.askopenfilenames(
            title="Select Files",
            filetypes=[("All files", "*.*")]
        )
        
        if files:
            self.add_files_to_list(files)
            self.log(f"Selected {len(files)} file(s)")

    def register_drop_target(self, widget):
        """Allow files to be dropped from the operating system onto a widget."""
        widget.drop_target_register(DND_FILES)
        widget.dnd_bind("<<Drop>>", self.on_files_dropped)

    def on_files_dropped(self, event):
        """Add files dropped from the operating system to the send queue."""
        files = self.root.tk.splitlist(event.data)
        valid_files = [filepath for filepath in files if os.path.isfile(filepath)]
        if not valid_files:
            self.log("Dropped items did not contain any files")
            return "copy"

        previous_count = len(self.selected_images)
        self.add_files_to_list(valid_files)
        added_count = len(self.selected_images) - previous_count
        self.log(f"Added {added_count} file(s) from drag and drop")
        return "copy"
    
    def add_files_to_list(self, files):
        """Add files to the list with auto-generated captions."""
        # Convert to list if tuple
        if isinstance(files, tuple):
            files = list(files)
        
        # Add to list
        start_index = len(self.selected_images)
        added_count = 0
        
        for filepath in files:
            if os.path.isfile(filepath):
                caption = f"Question {start_index + added_count + 1}"
                self.selected_images.append((filepath, caption))
                
                # Add to treeview
                idx = len(self.selected_images) - 1
                self.image_tree.insert("", "end", iid=idx,
                    values=(idx + 1, os.path.basename(filepath), caption))
                added_count += 1
        
        # Update UI
        self.files_label.config(text=f"{len(self.selected_images)} file(s) selected", foreground="black")
        self.selected_count_label.config(text=str(len(self.selected_images)))
        
        if self.caption_label:
            self.caption_label.config(text="Edit captions below and use drag or ↑↓ buttons to reorder files")
    
    def on_image_selected(self, event):
        """Handle image selection in treeview"""
        selection = self.image_tree.selection()
        if selection:
            item = selection[0]
            values = self.image_tree.item(item)["values"]
            caption = values[2]
            self.caption_entry.delete(0, tk.END)
            self.caption_entry.insert(0, caption)
            self.selection_info.set(f"Selected: {os.path.basename(values[1])} (Order: {int(values[0])})")
    
    def on_double_click(self, event):
        """Handle double-click to quickly edit a file caption."""
        self.on_image_selected(event)
    
    def update_caption(self):
        """Update caption for selected file."""
        selection = self.image_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a file first")
            return
        
        item = selection[0]
        values = self.image_tree.item(item)["values"]
        new_caption = self.caption_entry.get().strip()
        
        if not new_caption:
            messagebox.showwarning("Warning", "Caption cannot be empty")
            return
        
        idx = int(values[0]) - 1
        if idx < len(self.selected_images):
            filepath = self.selected_images[idx][0]
            self.selected_images[idx] = (filepath, new_caption)
            self.image_tree.item(item, values=(values[0], values[1], new_caption))
            self.log(f"Updated caption for {os.path.basename(values[1])}: {new_caption}")
    
    def move_up(self):
        """Move selected image up in order"""
        selection = self.image_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a file first")
            return
        
        item = selection[0]
        idx = int(self.image_tree.index(item))
        
        if idx == 0:
            messagebox.showinfo("Info", "Already at the top")
            return
        
        self.move_image_to(idx, idx - 1)
        self.log(f"Moved file up to position {idx}")
    
    def move_down(self):
        """Move selected image down in order"""
        selection = self.image_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a file first")
            return
        
        item = selection[0]
        idx = int(self.image_tree.index(item))
        
        if idx == len(self.selected_images) - 1:
            messagebox.showinfo("Info", "Already at the bottom")
            return
        
        self.move_image_to(idx, idx + 1)
        self.log(f"Moved file down to position {idx + 1}")
    
    def swap_next(self):
        """Swap selected image with next one"""
        selection = self.image_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a file first")
            return
        
        item = selection[0]
        idx = int(self.image_tree.index(item))
        
        if idx == len(self.selected_images) - 1:
            messagebox.showinfo("Info", "No next image to swap with")
            return
        
        self.move_image_to(idx, idx + 1)
        self.log("Swapped file with next one")
    
    def rebuild_treeview(self):
        """Rebuild treeview after reordering"""
        selected = self.image_tree.selection()
        selected_idx = int(self.image_tree.index(selected[0])) if selected else None
        
        for item in self.image_tree.get_children():
            self.image_tree.delete(item)
        
        for i, (filepath, caption) in enumerate(self.selected_images):
            self.image_tree.insert("", "end", iid=i,
                values=(i + 1, os.path.basename(filepath), caption))
        
        if selected_idx is not None:
            items = self.image_tree.get_children()
            if selected_idx < len(items):
                self.image_tree.selection_set(items[selected_idx])
    
    def auto_number_captions(self):
        """Auto-number all captions as Question 1, Question 2, etc."""
        for i, (filepath, caption) in enumerate(self.selected_images):
            new_caption = f"Question {i + 1}"
            self.selected_images[i] = (filepath, new_caption)
        
        self.rebuild_treeview()
        self.log("Auto-numbered all captions: Question 1, Question 2, etc.")
        messagebox.showinfo("Success", f"Updated {len(self.selected_images)} captions")
    
    def remove_selected(self):
        """Remove selected file from list"""
        selection = self.image_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a file first")
            return
        
        item = self.image_tree.selection()[0]
        idx = int(self.image_tree.index(item))
        filepath, caption = self.selected_images[idx]
        
        self.selected_images.pop(idx)
        self.rebuild_treeview()
        
        self.files_label.config(text=f"{len(self.selected_images)} file(s) selected", foreground="black")
        self.selected_count_label.config(text=str(len(self.selected_images)))
        
        self.log(f"Removed: {os.path.basename(filepath)}")
        
        if len(self.selected_images) == 0:
            if self.caption_label:
                self.caption_label.config(text="No files selected")
    
    def log(self, message):
        """Add message to log queue for thread-safe update"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_queue.put(f"[{timestamp}] {message}")
    
    def update_log_display(self):
        """Update log display from queue (called periodically)"""
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_text.config(state="normal")
                self.log_text.insert("end", message + "\n")
                self.log_text.see("end")
                self.log_text.config(state="disabled")
        except queue.Empty:
            pass
        
        self.root.after(100, self.update_log_display)
    
    def validate_credentials(self):
        """Validate bot token and chat ID"""
        if not self.bot_token.get().strip():
            messagebox.showerror("Error", "Please enter Bot Token")
            return False
        if not self.chat_id.get().strip():
            messagebox.showerror("Error", "Please enter Chat ID")
            return False
        
        if len(self.selected_images) == 0:
            messagebox.showerror("Error", "Please select at least one file")
            return False
        
        try:
            delay_val = float(self.delay_value.get())
            if delay_val <= 0:
                messagebox.showerror("Error", "Delay value must be greater than 0")
                return False
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number for delay")
            return False
        
        return True
    
    def get_delay_seconds(self):
        """Convert delay to seconds based on selected unit"""
        delay_val = float(self.delay_value.get())
        if self.delay_unit.get() == "minutes":
            return delay_val * 60
        return delay_val
    
    def send_file_to_telegram(self, image_path, caption):
        """Send supported photos as photos and all other files as documents."""
        try:
            extension = os.path.splitext(image_path)[1].lower()
            is_photo = (
                extension in {".jpg", ".jpeg", ".png"}
                and os.path.getsize(image_path) <= 10 * 1024 * 1024
            )
            method = "sendPhoto" if is_photo else "sendDocument"
            field = "photo" if is_photo else "document"
            url = f"https://api.telegram.org/bot{self.bot_token.get()}/{method}"
            mime_type = mimetypes.guess_type(image_path)[0] or "application/octet-stream"
            with open(image_path, "rb") as file_handle:
                files = {field: (os.path.basename(image_path), file_handle, mime_type)}
                data = {
                    "chat_id": self.chat_id.get(),
                    "caption": caption
                }
                
                response = requests.post(url, files=files, data=data, timeout=30)
                
                if is_photo and response.status_code != 200:
                    photo_error = response.text
                    file_handle.seek(0)
                    document_url = (
                        f"https://api.telegram.org/bot{self.bot_token.get()}/sendDocument"
                    )
                    document = {
                        "document": (
                            os.path.basename(image_path),
                            file_handle,
                            mime_type
                        )
                    }
                    response = requests.post(
                        document_url, files=document, data=data, timeout=30
                    )
                    if response.status_code != 200:
                        return False, (
                            f"Photo upload failed: {photo_error}; "
                            f"document fallback failed: {response.text}"
                        )

                if response.status_code == 200:
                    return True, None
                else:
                    return False, response.text
        except (OSError, requests.RequestException) as error:
            return False, str(error)
    
    def process_files(self):
        """Process and send all selected files."""
        self.is_running = True
        self.is_paused = False
        self.stop_requested = False
        
        delay_seconds = self.get_delay_seconds()
        
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.pause_btn.config(state="normal")
        self.select_btn.config(state="disabled")
        
        self.log(f"Processing started with {delay_seconds:.1f}s delay between files")
        self.log(f"Total files to send: {len(self.selected_images)}")
        
        total_images = len(self.selected_images)
        self.processed_images = 0
        self.error_count = 0
        
        for i, (image_path, caption) in enumerate(self.selected_images):
            if self.stop_requested:
                self.log("Processing stopped by user")
                break
            
            while self.is_paused and not self.stop_requested:
                time.sleep(0.5)
            
            if self.stop_requested:
                break
            
            self.processed_images += 1
            progress = (self.processed_images / total_images) * 100
            
            self.root.after(0, lambda p=progress, pcount=self.processed_images: self.update_progress(p, pcount))
            
            self.log(f"Sending file {self.processed_images}/{total_images}: {os.path.basename(image_path)}")
            self.log(f"  Caption: {caption}")
            
            success, error = self.send_file_to_telegram(image_path, caption)
            
            if success:
                self.log(f"✓ Sent: {os.path.basename(image_path)} | Caption: {caption}")
            else:
                self.error_count += 1
                self.root.after(0, lambda ec=self.error_count: self.error_count_label.config(text=str(ec)))
                self.log(f"✗ Error sending {os.path.basename(image_path)}: {error}")
            
            if i < total_images - 1 and not self.stop_requested:
                self.log(f"  Waiting {delay_seconds:.1f} seconds...")
                remaining_delay = delay_seconds
                while remaining_delay > 0:
                    if self.stop_requested:
                        break
                    if self.is_paused:
                        time.sleep(0.5)
                    else:
                        time.sleep(0.5)
                        remaining_delay -= 0.5
        
        self.is_running = False
        self.root.after(0, self.processing_complete)
    
    def update_progress(self, progress, processed_count):
        """Update progress bar and labels"""
        self.progress_bar["value"] = progress
        self.progress_label.config(text=f"{progress:.1f}%")
        self.processed_count_label.config(text=str(processed_count))
    
    def processing_complete(self):
        """Called when processing is complete"""
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.pause_btn.config(state="disabled")
        self.select_btn.config(state="normal")
        
        if self.stop_requested:
            self.log("Processing cancelled")
        else:
            self.log(f"Processing complete! Sent: {self.processed_images}, Errors: {self.error_count}")
            messagebox.showinfo("Complete", 
                f"Processing complete!\n\n"
                f"Selected: {len(self.selected_images)}\n"
                f"Processed: {self.processed_images}\n"
                f"Errors: {self.error_count}")
    
    def start_processing(self):
        """Start file processing in a separate thread."""
        if not self.selected_images:
            messagebox.showwarning("Warning", "Please select files first")
            return
        
        if not self.validate_credentials():
            return
        
        self.stop_requested = False
        self.is_paused = False
        self.pause_btn.config(text="Pause")
        
        self.log("Starting processing...")
        
        summary = "Files to send:\n"
        for i, (filepath, caption) in enumerate(self.selected_images):
            summary += f"  {i+1}. {os.path.basename(filepath)} - \"{caption}\"\n"
        self.log(summary)
        
        thread = threading.Thread(target=self.process_files, daemon=True)
        thread.start()
    
    def stop_processing(self):
        """Stop processing"""
        if self.is_running:
            self.stop_requested = True
            self.log("Stop requested...")
    
    def toggle_pause(self):
        """Pause/resume processing"""
        if not self.is_running:
            return
        
        self.is_paused = not self.is_paused
        
        if self.is_paused:
            self.pause_btn.config(text="Resume")
            self.log("Processing paused")
        else:
            self.pause_btn.config(text="Pause")
            self.log("Processing resumed")


def main():
    root = TkinterDnD.Tk()
    app = TelegramImageSender(root)
    root.mainloop()


if __name__ == "__main__":
    main()