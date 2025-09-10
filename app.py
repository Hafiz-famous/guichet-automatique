from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from decimal import Decimal, InvalidOperation
from models import Bank, parse_amount, as_money

import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "accounts.json")


class ATMApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ATM Interface - Tkinter")
        self.geometry("880x560")
        self.resizable(False, False)

        # Theme
        self.style = ttk.Style(self)
        # use default theme; ensure consistent widget look
        self.style.theme_use(self.style.theme_names()[0])

        # State
        self.bank = Bank(DATA_PATH)
        self.current_card = None  # str

        # container for frames
        container = ttk.Frame(self, padding=12)
        container.pack(fill="both", expand=True)

        self.frames = {}
        for F in (LoginFrame, HomeFrame, DepositFrame, WithdrawFrame, TransferFrame, PinChangeFrame, HistoryFrame):
            frame = F(parent=container, controller=self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show("LoginFrame")

    def show(self, name: str):
        frame = self.frames[name]
        frame.tkraise()
        if hasattr(frame, "on_show"):
            frame.on_show()

    # ---------- helpers ----------
    def require_session(self):
        if not self.current_card:
            self.show("LoginFrame")
            raise RuntimeError("Not logged in")

    def logout(self):
        self.current_card = None
        self.show("LoginFrame")


# =============== Frames ===============

class LoginFrame(ttk.Frame):
    def __init__(self, parent, controller: ATMApp):
        super().__init__(parent)
        self.controller = controller

        title = ttk.Label(self, text="Bienvenue — Guichet Automatique", font=("Segoe UI", 18, "bold"))
        title.pack(pady=(10, 20))

        form = ttk.Frame(self)
        form.pack(pady=10)

        ttk.Label(form, text="Numéro de carte").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.card_var = tk.StringVar()
        self.card_entry = ttk.Entry(form, textvariable=self.card_var, width=30)
        self.card_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(form, text="PIN").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.pin_var = tk.StringVar()
        self.pin_entry = ttk.Entry(form, textvariable=self.pin_var, show="•", width=30)
        self.pin_entry.grid(row=1, column=1, padx=5, pady=5)

        self.status = ttk.Label(self, text="", foreground="#b22222")
        self.status.pack(pady=(8, 0))

        btns = ttk.Frame(self)
        btns.pack(pady=15)
        ttk.Button(btns, text="Se connecter", command=self.login).grid(row=0, column=0, padx=6)
        ttk.Button(btns, text="Quitter", command=self.controller.destroy).grid(row=0, column=1, padx=6)

        self.card_entry.focus_set()

    def login(self):
        card = self.card_var.get().strip()
        pin = self.pin_var.get().strip()
        if not card or not pin:
            self.status.config(text="Veuillez saisir carte et PIN.")
            return
        try:
            acc = self.controller.bank.authenticate(card, pin)
        except Exception as e:
            self.status.config(text=str(e))
            self.pin_var.set("")
            self.pin_entry.focus_set()
            return
        self.controller.current_card = acc.card_number
        self.card_var.set("")
        self.pin_var.set("")
        self.status.config(text="")
        self.controller.show("HomeFrame")


class HomeFrame(ttk.Frame):
    def __init__(self, parent, controller: ATMApp):
        super().__init__(parent)
        self.controller = controller
        self.name_lbl = ttk.Label(self, text="", font=("Segoe UI", 16, "bold"))
        self.name_lbl.pack(pady=(10, 5))

        self.balance_lbl = ttk.Label(self, text="", font=("Segoe UI", 14))
        self.balance_lbl.pack(pady=(0, 20))

        grid = ttk.Frame(self)
        grid.pack(pady=10)

        ttk.Button(grid, text="Dépôt", width=20, command=lambda: controller.show("DepositFrame")).grid(row=0, column=0, padx=10, pady=10)
        ttk.Button(grid, text="Retrait", width=20, command=lambda: controller.show("WithdrawFrame")).grid(row=0, column=1, padx=10, pady=10)
        ttk.Button(grid, text="Virement", width=20, command=lambda: controller.show("TransferFrame")).grid(row=0, column=2, padx=10, pady=10)
        ttk.Button(grid, text="Historique", width=20, command=lambda: controller.show("HistoryFrame")).grid(row=1, column=0, padx=10, pady=10)
        ttk.Button(grid, text="Changer PIN", width=20, command=lambda: controller.show("PinChangeFrame")).grid(row=1, column=1, padx=10, pady=10)
        ttk.Button(grid, text="Se déconnecter", width=20, command=controller.logout).grid(row=1, column=2, padx=10, pady=10)

    def on_show(self):
        try:
            self.controller.require_session()
        except RuntimeError:
            return
        acc = self.controller.bank.get_account(self.controller.current_card)
        self.name_lbl.config(text=f"Bonjour, {acc.name}")
        self.balance_lbl.config(text=f"Solde: {acc.balance}")

class AmountFrameBase(ttk.Frame):
    title = "Opération"
    button_text = "Valider"

    def __init__(self, parent, controller: ATMApp):
        super().__init__(parent)
        self.controller = controller
        ttk.Label(self, text=self.title, font=("Segoe UI", 16, "bold")).pack(pady=(10, 10))
        form = ttk.Frame(self)
        form.pack(pady=10)
        ttk.Label(form, text="Montant").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.amount_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.amount_var, width=30).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(form, text="Note (facultatif)").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.note_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.note_var, width=30).grid(row=1, column=1, padx=5, pady=5)

        self.status = ttk.Label(self, text="", foreground="#b22222")
        self.status.pack(pady=(5, 0))

        btns = ttk.Frame(self)
        btns.pack(pady=10)
        ttk.Button(btns, text=self.button_text, command=self.submit).grid(row=0, column=0, padx=6)
        ttk.Button(btns, text="Retour", command=lambda: controller.show("HomeFrame")).grid(row=0, column=1, padx=6)

    def submit(self):
        raise NotImplementedError

    def get_amount(self) -> Decimal:
        txt = self.amount_var.get().strip()
        try:
            amt = parse_amount(txt)
        except (InvalidOperation, ValueError):
            raise ValueError("Montant invalide.")
        if amt <= 0:
            raise ValueError("Montant invalide.")
        return amt

class DepositFrame(AmountFrameBase):
    title = "Dépôt"
    button_text = "Déposer"

    def submit(self):
        try:
            self.controller.require_session()
            amount = self.get_amount()
            new_bal = self.controller.bank.deposit(self.controller.current_card, amount, self.note_var.get())
            messagebox.showinfo("Succès", f"Dépôt effectué.\nNouveau solde: {new_bal}")
            self.amount_var.set("")
            self.note_var.set("")
            self.controller.show("HomeFrame")
        except Exception as e:
            self.status.config(text=str(e))

class WithdrawFrame(AmountFrameBase):
    title = "Retrait"
    button_text = "Retirer"

    def submit(self):
        try:
            self.controller.require_session()
            amount = self.get_amount()
            new_bal = self.controller.bank.withdraw(self.controller.current_card, amount, self.note_var.get())
            messagebox.showinfo("Succès", f"Retrait effectué.\nNouveau solde: {new_bal}")
            self.amount_var.set("")
            self.note_var.set("")
            self.controller.show("HomeFrame")
        except Exception as e:
            self.status.config(text=str(e))

class TransferFrame(AmountFrameBase):
    title = "Virement"
    button_text = "Envoyer"

    def __init__(self, parent, controller: ATMApp):
        super().__init__(parent, controller)
        # add target field
        form2 = ttk.Frame(self)
        form2.pack(pady=4)
        ttk.Label(form2, text="Carte destinataire").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.target_var = tk.StringVar()
        ttk.Entry(form2, textvariable=self.target_var, width=30).grid(row=0, column=1, padx=5, pady=5)

    def submit(self):
        try:
            self.controller.require_session()
            target = self.target_var.get().strip()
            if not target:
                raise ValueError("Saisir la carte destinataire.")
            amount = self.get_amount()
            self.controller.bank.transfer(self.controller.current_card, target, amount, self.note_var.get())
            messagebox.showinfo("Succès", "Virement effectué.")
            self.amount_var.set("")
            self.note_var.set("")
            self.target_var.set("")
            self.controller.show("HomeFrame")
        except Exception as e:
            self.status.config(text=str(e))

class PinChangeFrame(ttk.Frame):
    def __init__(self, parent, controller: ATMApp):
        super().__init__(parent)
        self.controller = controller

        ttk.Label(self, text="Changer le PIN", font=("Segoe UI", 16, "bold")).pack(pady=(10, 10))
        form = ttk.Frame(self); form.pack(pady=10)
        ttk.Label(form, text="Ancien PIN").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.old_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.old_var, show="•", width=30).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(form, text="Nouveau PIN (4-6 chiffres)").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.new_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.new_var, show="•", width=30).grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(form, text="Confirmer PIN").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.conf_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.conf_var, show="•", width=30).grid(row=2, column=1, padx=5, pady=5)

        self.status = ttk.Label(self, text="", foreground="#b22222")
        self.status.pack(pady=(5, 0))

        btns = ttk.Frame(self); btns.pack(pady=10)
        ttk.Button(btns, text="Mettre à jour", command=self.submit).grid(row=0, column=0, padx=6)
        ttk.Button(btns, text="Retour", command=lambda: controller.show("HomeFrame")).grid(row=0, column=1, padx=6)

    def submit(self):
        try:
            self.controller.require_session()
            old = self.old_var.get().strip()
            new = self.new_var.get().strip()
            conf = self.conf_var.get().strip()
            if new != conf:
                raise ValueError("Les PIN ne correspondent pas.")
            self.controller.bank.change_pin(self.controller.current_card, old, new)
            messagebox.showinfo("Succès", "PIN mis à jour.")
            self.old_var.set(""); self.new_var.set(""); self.conf_var.set("")
            self.controller.show("HomeFrame")
        except Exception as e:
            self.status.config(text=str(e))

class HistoryFrame(ttk.Frame):
    def __init__(self, parent, controller: ATMApp):
        super().__init__(parent)
        self.controller = controller
        ttk.Label(self, text="Historique des transactions", font=("Segoe UI", 16, "bold")).pack(pady=(10, 10))

        self.tree = ttk.Treeview(self, columns=("date", "type", "montant", "contrepartie", "note"), show="headings", height=16)
        self.tree.heading("date", text="Date (UTC)")
        self.tree.heading("type", text="Type")
        self.tree.heading("montant", text="Montant")
        self.tree.heading("contrepartie", text="Contrepartie")
        self.tree.heading("note", text="Note")
        self.tree.column("date", width=160)
        self.tree.column("type", width=120)
        self.tree.column("montant", width=120)
        self.tree.column("contrepartie", width=140)
        self.tree.column("note", width=280)
        self.tree.pack(fill="both", expand=True, padx=12, pady=8)

        btns = ttk.Frame(self); btns.pack(pady=8)
        ttk.Button(btns, text="Retour", command=lambda: controller.show("HomeFrame")).grid(row=0, column=0, padx=6)

    def on_show(self):
        try:
            self.controller.require_session()
        except RuntimeError:
            return
        # clear
        for item in self.tree.get_children():
            self.tree.delete(item)
        txs = self.controller.bank.transactions_of(self.controller.current_card)
        for t in txs:
            self.tree.insert("", "end", values=(t.timestamp, t.type, t.amount, t.counterparty or "", t.note or ""))


if __name__ == "__main__":
    app = ATMApp()
    app.mainloop()
