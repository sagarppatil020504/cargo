import tkinter as tk
from tkinter import messagebox, ttk
import requests

API_BASE = "http://127.0.0.1:8000"

class ItemManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SQLite Item Manager")
        # Entry fields
        self.fields = ["item_id", "item_name", "length", "width", "height", "mass", "priority",
                       "expiry_date", "usage_limit", "zone", "used_units"]
        self.entries = {}
        for idx, field in enumerate(self.fields):
            tk.Label(root, text=field.replace("_", " ").capitalize()).grid(row=idx, column=0, padx=5, pady=5, sticky="e")
            entry = tk.Entry(root)
            entry.grid(row=idx, column=1, padx=5, pady=5)
            self.entries[field] = entry

        # Buttons
        tk.Button(root, text="Add Item", command=self.add_item).grid(row=0, column=2, padx=10)
        tk.Button(root, text="Update Item", command=self.update_item).grid(row=1, column=2, padx=10)
        tk.Button(root, text="Delete Item", command=self.delete_item).grid(row=2, column=2, padx=10)
        tk.Button(root, text="Search", command=self.search_item).grid(row=3, column=2, padx=10)
        tk.Button(root, text="Load All", command=self.load_all_items).grid(row=4, column=2, padx=10)

        # Treeview table
        self.tree = ttk.Treeview(root, columns=self.fields, show="headings")
        for field in self.fields:
            self.tree.heading(field, text=field.replace("_", " ").capitalize())
        self.tree.grid(row=15, column=0, columnspan=3, padx=10, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

    def get_form_data(self):
        return {field: self.entries[field].get() for field in self.fields}

    def set_form_data(self, data):
        for field in self.fields:
            self.entries[field].delete(0, tk.END)
            self.entries[field].insert(0, str(data.get(field, "")))

    def clear_form(self):
        for entry in self.entries.values():
            entry.delete(0, tk.END)

    def add_item(self):
        data = self.get_form_data()
        try:
            data["item_id"] = int(data["item_id"])
            data["length"] = float(data["length"])
            data["width"] = float(data["width"])
            data["height"] = float(data["height"])
            data["mass"] = float(data["mass"])
            data["priority"] = float(data["priority"])
            data["usage_limit"] = int(data["usage_limit"])
            data["used_units"] = int(data["used_units"])
        except ValueError:
            messagebox.showerror("Error", "Please check your input types.")
            return

        response = requests.post(f"{API_BASE}/items", json=data)
        if response.status_code == 200:
            messagebox.showinfo("Success", "Item added successfully.")
            self.clear_form()
            self.load_all_items()
        else:
            messagebox.showerror("Error", f"Failed to add item.\n{response.text}")

    def update_item(self):
        item_id = self.entries["item_id"].get()
        if not item_id:
            messagebox.showerror("Error", "Item ID required for update.")
            return
        data = self.get_form_data()
        try:
            response = requests.put(f"{API_BASE}/items/{item_id}", json=data)
            if response.status_code == 200:
                messagebox.showinfo("Success", "Item updated.")
                self.load_all_items()
            else:
                raise Exception(response.text)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_item(self):
        item_id = self.entries["item_id"].get()
        if not item_id:
            messagebox.showerror("Error", "Item ID required for deletion.")
            return
        response = requests.delete(f"{API_BASE}/items/{item_id}")
        if response.status_code == 200:
            messagebox.showinfo("Deleted", "Item deleted.")
            self.clear_form()
            self.load_all_items()
        else:
            messagebox.showerror("Error", f"Failed to delete.\n{response.text}")

    def search_item(self):
        item_id = self.entries["item_id"].get()
        item_name = self.entries["item_name"].get()

        if item_id:
            response = requests.get(f"{API_BASE}/items/{item_id}")
        elif item_name:
            response = requests.get(f"{API_BASE}/search?item_name={item_name}")
        else:
            messagebox.showerror("Error", "Enter Item ID or Name to search.")
            return

        if response.status_code == 200:
            item = response.json()
            if isinstance(item, list):
                item = item[0]
            self.set_form_data(item)
        else:
            messagebox.showerror("Not Found", "Item not found.")

    def load_all_items(self):
        response = requests.get(f"{API_BASE}/items")
        if response.status_code == 200:
            self.tree.delete(*self.tree.get_children())
            for item in response.json():
                values = [item.get(field, "") for field in self.fields]
                self.tree.insert("", "end", values=values)
        else:
            messagebox.showerror("Error", "Could not load items.")

    def on_tree_select(self, event):
        selected = self.tree.selection()
        if selected:
            values = self.tree.item(selected[0])["values"]
            for i, field in enumerate(self.fields):
                self.entries[field].delete(0, tk.END)
                self.entries[field].insert(0, str(values[i]))

if __name__ == "__main__":
    root = tk.Tk()
    app = ItemManagerApp(root)
    root.mainloop()
