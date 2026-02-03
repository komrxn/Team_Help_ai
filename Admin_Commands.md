# 🛠 TeamHub Admin Cheatsheet

## 🚀 Deployment & Updates

### 1. Update Code
To pull the latest changes from GitHub:
```bash
git pull origin main
```

### 2. Restart Services
After pulling code or changing `.env`, restart the bots:
```bash
# Smooth restart (rebuilds if needed)
docker compose up -d --build

# View logs (real-time)
docker compose logs -f

# View logs for specific bot
docker compose logs -f admin_bot
docker compose logs -f driver_bot
```

### 3. Database Management
```bash
# Restart database only
docker compose restart postgres

# Reset Database (⚠️ DELETES ALL DATA)
docker compose down -v
docker compose up -d --build
```

---

## ⚡ Admin Bot Commands
*Commands only work in the designated Admin Group.*

### 🚙 Driver Management
| Command | Description | Example |
| :--- | :--- | :--- |
| `/drivers` | **List Active Drivers**<br>Shows location, last seen time, and rating. | `/drivers` |
| `/find` | **Find Driver**<br>Interactive menu to search by State/City. | `/find` |
| `/find [State]` | **Quick Find**<br>Search directly by state code. | `/find NY` |
| `/approve [ID]` | **Approve New Driver**<br>Instantly activates a pending driver. | `/approve 12345678` |
| `/delete` | **Delete Driver**<br>Menu to remove a driver from the system. | `/delete` |
| `/delete [ID]` | **Quick Delete**<br>Directly delete by User ID. | `/delete 12345678` |

### 📊 Reports & Rating
| Command | Description | Example |
| :--- | :--- | :--- |
| `/rate` | **Rate Driver**<br>Menu to rate a completed order (Good/Bad). | `/rate` |
| `/rate [ID]` | **Quick Rate**<br>Rate a specific driver immediately. | `/rate 12345678` |
| `/export` | **Export CSV**<br>Download full list of drivers as `.csv` file. | `/export` |

### ⚙️ System
| Command | Description |
| :--- | :--- |
| `/id` | Get current Chat ID (useful for setup). |
| `/help` | Show list of available commands. |

---

## 🤖 Driver Bot (User Side)
*Commands for drivers/users.*

| Command | Description |
| :--- | :--- |
| `/start` | Register or Open Main Menu. |
| `/location` | Share/Update current location. |
| `/help` | Show help message. |

---

## 🔧 Troubleshooting
**Bot not responding?**
1. Check logs: `docker compose logs -f --tail=100`
2. Restart: `docker compose restart`

**Duplicate Drivers in List?**
* Run `/drivers` again (fixed in v1.0).
* Use `/refresh` button on the list.
