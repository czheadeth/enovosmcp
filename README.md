# ⚡ Enovos MCP - AI-Powered Energy Assistant

> 🏆 **Hackathon Project**: Enabling conversational energy management through ChatGPT

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP Protocol](https://img.shields.io/badge/MCP-1.0-green.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🎯 The Problem

Energy customers struggle to:
- 📊 Understand their consumption patterns
- 📝 Know if they have the right contract for their profile
- 💰 Find ways to save money and reduce their carbon footprint
- 🤝 Discover energy sharing opportunities

**Traditional solutions** require navigating complex portals, reading charts, and understanding energy jargon.

---

## 💡 Our Solution

An **MCP (Model Context Protocol) server** that connects Enovos customer data directly to ChatGPT, enabling natural conversations like:

> *"Am I on the right energy contract?"*  
> *"How can I save money on my energy bill?"*  
> *"Find me Energy Sharing partners nearby"*  
> *"What challenges can I participate in this month?"*

**ChatGPT becomes your personal energy advisor** - understanding your consumption profile, recommending the best offers, and helping you save money.

---

## 🏗️ Architecture

```
┌─────────────────┐       HTTPS/SSE        ┌───────────────────────────┐
│                 │◄──────────────────────►│      AWS EC2 Instance     │
│    ChatGPT      │        (ngrok)         │                           │
│   (Frontend)    │                        │   ┌───────────────────┐   │
│                 │                        │   │    MCP Server     │   │
└─────────────────┘                        │   │  (Python/FastMCP) │   │
        │                                  │   └─────────┬─────────┘   │
        │                                  │             │             │
   User asks                               │   ┌─────────▼─────────┐   │
   questions                               │   │   Load Curve      │   │
        │                                  │   │   Data (CSV)      │   │
        ▼                                  │   │   50+ customers   │   │
┌─────────────────┐                        │   └───────────────────┘   │
│  AI interprets  │                        │                           │
│  and responds   │                        └───────────────────────────┘
└─────────────────┘                                     │
                                                        ▼ (Roadmap)
                                               ┌───────────────┐
                                               │   DynamoDB    │
                                               │  (Scalable)   │
                                               └───────────────┘
```

### Why ngrok?

ChatGPT requires **HTTPS endpoints** for MCP connectors. Instead of managing SSL certificates on EC2, we use **ngrok** to create a secure tunnel. This allows rapid prototyping without infrastructure complexity.

---

## 🛠️ MCP Tools (10 Services)

### 📊 Consumption Data
| Tool | Description |
|------|-------------|
| `get_consumption_hourly` | Hourly consumption (max 7 days) |
| `get_consumption_daily` | Daily consumption (max 90 days) |
| `get_consumption_monthly` | Monthly consumption |

### 🧠 Smart Analysis
| Tool | Description |
|------|-------------|
| `get_customer_profile` | AI classification: **EV**, **heat_pump**, **office**, or **residential** |
| `get_customer_contract` | Current contract details |
| `get_enovos_offers` | All available energy offers with `ideal_for` matching |
| `get_advice` | Smart workflow for personalized recommendations |

### 🎮 Engagement & Community
| Tool | Description |
|------|-------------|
| `get_challenges` | Energy saving challenges with rewards (€10-15 credits) |
| `find_sharing_partners` | Find solar producers for Energy Sharing (save up to 10%) |
| `signal_interest` | Register interest in Energy Sharing partnership |

---

## 🔮 Profile Classification

The system automatically classifies customers based on their consumption patterns:

| Profile | Detection | Recommended Offer |
|---------|-----------|-------------------|
| 🚗 **EV Owner** | Night consumption > Day × 1.5 | Naturstrom Drive (-40% night) |
| 🔥 **Heat Pump** | Winter/Summer ratio > 2.0 | Naturstrom Fix (stable price) |
| 🏢 **Office** | Day consumption > Night × 1.5 | Energy Sharing (network savings) |
| 🏠 **Residential** | Standard pattern | Nova Naturstroum (100% green) |

---

## 🚀 Demo Scenarios

### Scenario 1: Contract Optimization
```
User: "Am I on the right contract?"

ChatGPT: 
1. Calls get_customer_profile → detects "ev" profile
2. Calls get_customer_contract → sees "Naturstrom Fix"
3. Calls get_enovos_offers → finds "Naturstrom Drive" is ideal for EV
4. Recommends switching → save 40% on night charging!
```

### Scenario 2: Energy Sharing
```
User: "How can I reduce my network fees?"

ChatGPT:
1. Calls get_customer_profile → detects "office" (high daytime use)
2. Calls find_sharing_partners → finds 3 solar producers nearby
3. Suggests partnership → save up to 10% on network fees!
4. User calls signal_interest → Enovos contacts both parties
```

### Scenario 3: Gamification
```
User: "Any tips to save energy?"

ChatGPT:
1. Calls get_advice → gets workflow
2. Calls get_challenges → finds "Peak Hour Challenge"
3. Invites user to reduce 19:00-20:00 consumption
4. Reward: €10 bill credit!
```

---

## ⚙️ Technical Setup

### Prerequisites
- AWS EC2 instance (Amazon Linux 2 / t2.micro)
- Python 3.11+
- ngrok account ([free tier](https://ngrok.com/))
- GitHub repository access

### Installation on EC2

```bash
# 1. Connect to EC2
ssh -i "your-key.pem" ec2-user@your-ec2-ip

# 2. Clone repository
git clone https://github.com/czheadeth/enovosmcp.git
cd enovosmcp

# 3. Install Python 3.11 (if needed)
sudo yum install python3.11 -y

# 4. Install dependencies
python3.11 -m pip install -r requirements.txt

# 5. Add your data files to src/data/
# (CSV files with load curves)

# 6. Start the MCP server
nohup python3.11 -m src.server > server.log 2>&1 &

# 7. Verify it's running
curl http://localhost:8000/
# Should return: {"status":"ok","server":"enovos-mcp"}
```

### Setup ngrok

```bash
# Download ngrok
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar -xzf ngrok-v3-stable-linux-amd64.tgz

# Configure auth token
./ngrok config add-authtoken YOUR_TOKEN

# Start tunnel
./ngrok http 8000
```

### Connect to ChatGPT

1. Open [ChatGPT](https://chat.openai.com/)
2. Go to **Settings** → **Connectors** → **Add Connector**
3. Select **MCP**
4. Paste your ngrok URL: `https://xxx.ngrok-free.dev/mcp/sse`
5. Start chatting! 🎉

---

## 📊 Data Format

### Load Curve CSV Structure
```csv
timestamp,value
2023-01-01 00:00:00,0.45
2023-01-01 00:15:00,0.42
2023-01-01 00:30:00,0.38
...
```

- **timestamp**: 15-minute intervals
- **value**: Consumption in kWh
- **Duration**: ~2 years per customer

### File Naming Convention
```
LU_ENO_DELPHI_LU_virtual_ind_00001.csv
                            └─────┘
                          Customer ID
```

---

## 🌟 Key Innovations

1. **🧠 AI Profile Detection** - Automatically identifies EV owners, heat pumps, offices based on consumption patterns

2. **🎯 Smart Matching** - Matches customer profile to ideal contract, suggests savings

3. **🤝 Energy Sharing** - Connects daytime consumers (offices) with solar producers (residents)

4. **🎮 Gamification** - Challenges with real rewards to encourage peak-hour savings

5. **💬 Natural Language** - No portals, no charts - just ask ChatGPT!

---

## 🗺️ Roadmap

- [x] Core MCP server with consumption tools
- [x] Profile classification (EV, heat pump, office, residential)
- [x] Contract recommendation engine
- [x] Energy Sharing partner matching
- [x] Gamification with challenges
- [ ] DynamoDB integration for scalability
- [ ] Real-time consumption data
- [ ] Push notifications for challenges
- [ ] Multi-language support (FR, DE, LU)

---

## 🧪 Testing Locally

```bash
# Run server locally
python -m src.server

# Test endpoints
curl http://localhost:8000/
curl http://localhost:8000/health
```

---

## 📁 Project Structure

```
enovosmcp/
├── src/
│   ├── server.py          # Main MCP server (10 tools)
│   ├── clustering.py      # Profile clustering utilities
│   └── data/              # Customer load curves (CSV)
├── scripts/
│   ├── generate_ev_profile.py
│   └── find_ev_profiles.py
├── requirements.txt
├── Dockerfile
└── README.md
```

---

## 👥 Team

**Enovos Luxembourg** - Energy Hackathon 2024

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

<p align="center">
  <b>⚡ Transforming energy management through conversational AI ⚡</b>
</p>
