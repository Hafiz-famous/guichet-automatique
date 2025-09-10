from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP, getcontext
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import hashlib
import json
import os

getcontext().prec = 28  # high precision for money arithmetic


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def as_money(value: Decimal) -> Decimal:
    # round HALF_UP to 2 decimals
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def parse_amount(text: str) -> Decimal:
    text = text.replace(",", ".").strip()
    return Decimal(text)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class Transaction:
    type: str  # 'deposit', 'withdraw', 'transfer_out', 'transfer_in', 'pin_change'
    amount: str  # stored as str for JSON (two decimals), e.g. "100.00"
    timestamp: str  # ISO 8601 UTC string
    counterparty: Optional[str] = None  # target/source card for transfers
    note: Optional[str] = ""


@dataclass
class Account:
    card_number: str
    name: str
    pin_hash: str
    balance: str  # stored as str for JSON
    transactions: List[Transaction] = field(default_factory=list)
    failed_attempts: int = 0
    is_locked: bool = False

    # --- runtime helpers (not stored) ---
    def balance_decimal(self) -> Decimal:
        return Decimal(self.balance)

    def set_balance(self, value: Decimal) -> None:
        self.balance = f"{as_money(value):.2f}"


class Bank:
    def __init__(self, path: str) -> None:
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.data: Dict[str, Account] = {}
        self._load_or_seed()

    # ---------------- Persistence ----------------
    def _load_or_seed(self) -> None:
        if not os.path.exists(self.path):
            self._seed_default()
            self._save()
            return
        with open(self.path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        self.data = {}
        for card, acc in raw.get("accounts", {}).items():
            txs = [Transaction(**t) for t in acc.get("transactions", [])]
            self.data[card] = Account(
                card_number=card,
                name=acc["name"],
                pin_hash=acc["pin_hash"],
                balance=acc["balance"],
                transactions=txs,
                failed_attempts=acc.get("failed_attempts", 0),
                is_locked=acc.get("is_locked", False),
            )

    def _save(self) -> None:
        raw = {"accounts": {}}
        for card, acc in self.data.items():
            raw["accounts"][card] = {
                "name": acc.name,
                "pin_hash": acc.pin_hash,
                "balance": acc.balance,
                "transactions": [t.__dict__ for t in acc.transactions],
                "failed_attempts": acc.failed_attempts,
                "is_locked": acc.is_locked,
            }
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(raw, f, indent=2, ensure_ascii=False)

    def _seed_default(self) -> None:
        # default demo accounts
        self.data = {}
        self.data["12345678"] = Account(
            card_number="12345678",
            name="Alice",
            pin_hash=sha256_hex("1234"),
            balance="500.00",
            transactions=[
                Transaction(type="deposit", amount="500.00", timestamp=now_iso(), note="Seed")
            ],
        )
        self.data["87654321"] = Account(
            card_number="87654321",
            name="Bob",
            pin_hash=sha256_hex("4321"),
            balance="1000.00",
            transactions=[
                Transaction(type="deposit", amount="1000.00", timestamp=now_iso(), note="Seed")
            ],
        )

    # ---------------- Auth ----------------
    def authenticate(self, card_number: str, pin: str) -> Account:
        acc = self.data.get(card_number)
        if not acc:
            raise ValueError("Carte inconnue.")
        if acc.is_locked:
            raise PermissionError("Compte verrouillé après plusieurs essais.")

        if acc.pin_hash == sha256_hex(pin):
            # reset attempts on success
            acc.failed_attempts = 0
            self._save()
            return acc

        # failed attempt
        acc.failed_attempts += 1
        if acc.failed_attempts >= 3:
            acc.is_locked = True
        self._save()
        if acc.is_locked:
            raise PermissionError("Compte verrouillé après 3 échecs PIN.")
        raise ValueError("PIN incorrect.")

    # ---------------- Queries ----------------
    def get_account(self, card_number: str) -> Account:
        if card_number not in self.data:
            raise ValueError("Carte inconnue.")
        return self.data[card_number]

    def balance_of(self, card_number: str) -> Decimal:
        return self.get_account(card_number).balance_decimal()

    # ---------------- Operations ----------------
    def deposit(self, card_number: str, amount: Decimal, note: str = "") -> Decimal:
        if amount <= 0:
            raise ValueError("Montant invalide.")
        acc = self.get_account(card_number)
        new_bal = as_money(acc.balance_decimal() + amount)
        acc.set_balance(new_bal)
        acc.transactions.append(Transaction("deposit", f"{as_money(amount):.2f}", now_iso(), note=note))
        self._save()
        return new_bal

    def withdraw(self, card_number: str, amount: Decimal, note: str = "") -> Decimal:
        if amount <= 0:
            raise ValueError("Montant invalide.")
        acc = self.get_account(card_number)
        if acc.balance_decimal() < amount:
            raise ValueError("Solde insuffisant.")
        new_bal = as_money(acc.balance_decimal() - amount)
        acc.set_balance(new_bal)
        acc.transactions.append(Transaction("withdraw", f"{as_money(amount):.2f}", now_iso(), note=note))
        self._save()
        return new_bal

    def transfer(self, source_card: str, target_card: str, amount: Decimal, note: str = "") -> None:
        if amount <= 0:
            raise ValueError("Montant invalide.")
        if source_card == target_card:
            raise ValueError("Impossible de transférer vers le même compte.")
        src = self.get_account(source_card)
        tgt = self.get_account(target_card)
        if src.balance_decimal() < amount:
            raise ValueError("Solde insuffisant.")
        # debit
        src.set_balance(as_money(src.balance_decimal() - amount))
        src.transactions.append(Transaction("transfer_out", f"{as_money(amount):.2f}", now_iso(), counterparty=target_card, note=note))
        # credit
        tgt.set_balance(as_money(tgt.balance_decimal() + amount))
        tgt.transactions.append(Transaction("transfer_in", f"{as_money(amount):.2f}", now_iso(), counterparty=source_card, note=note))
        self._save()

    def change_pin(self, card_number: str, old_pin: str, new_pin: str) -> None:
        acc = self.get_account(card_number)
        if acc.pin_hash != sha256_hex(old_pin):
            raise ValueError("Ancien PIN incorrect.")
        if not (4 <= len(new_pin) <= 6 and new_pin.isdigit()):
            raise ValueError("Le PIN doit être 4 à 6 chiffres.")
        acc.pin_hash = sha256_hex(new_pin)
        acc.failed_attempts = 0
        acc.is_locked = False
        acc.transactions.append(Transaction("pin_change", "0.00", now_iso(), note="PIN mis à jour"))
        self._save()

    def transactions_of(self, card_number: str) -> List[Transaction]:
        return self.get_account(card_number).transactions
