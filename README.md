# ATM Interface Project — Tkinter (Python)

Une interface **ATM** (guichet automatique) réaliste construite avec **Tkinter/ttk**, sans dépendance externe.
Fonctions: connexion (numéro de carte + PIN), solde, dépôt, retrait, virement, changement de PIN, historique des transactions, verrouillage après 3 échecs.

## 🔧 Prérequis
- Python **3.9+** (testé 3.10+)
- Aucune dépendance externe (Tkinter est inclus avec Python standard)

## ▶️ Démarrage
```bash
# 1) Dézippez le dossier
# 2) Ouvrez le dossier dans VS Code
# 3) Exécutez :
python app.py
```

> La première exécution **générera automatiquement** `data/accounts.json` avec 2 comptes de test.

### Comptes de test
- **Carte**: `12345678` — **PIN**: `1234` — Solde initial: `500.00`
- **Carte**: `87654321` — **PIN**: `4321` — Solde initial: `1000.00`

> ⚠️ **Sécurité**: Ce projet est une **simulation** éducative **non destinée** à un usage bancaire réel.

## 🧱 Structure
```
atm_tkinter/
├── app.py                # UI Tkinter/ttk & navigation
├── models.py             # Logique métier (Bank, Account, Transactions)
├── data/
│   └── accounts.json     # Stockage "fichier" (auto-créé si absent)
├── LICENSE               # MIT
└── README.md
```

## ✨ Fonctions principales
- Authentification par **numéro de carte + PIN** (3 essais, puis verrouillage)
- **Solde** en temps réel
- **Dépôt / Retrait** (validation des montants)
- **Virement** entre comptes existants
- **Changement de PIN**
- **Historique** détaillé (type, montant, date, contrepartie, note)
- Persistance **JSON** simple

## 🧪 Conseils
- Les montants utilisent `Decimal` pour éviter les erreurs d'arrondi.
- Les données sont enregistrées **après chaque opération**.
- Pour réinitialiser les comptes, supprimez `data/accounts.json` et relancez l'app.

## 📄 Licence
MIT — libre d'utilisation et de modification.
