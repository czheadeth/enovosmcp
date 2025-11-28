# ⚡ Enovos MCP - Be Present Where Your Customers Are

> 🏆 **Hackathon Project**: Anticipating the AI revolution in customer relationships

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP Protocol](https://img.shields.io/badge/MCP-1.0-green.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🌍 The Context

**ChatGPT has been the most downloaded app in the world for over a year.**

General-purpose AI tools are becoming the central channel through which people accomplish everything - from booking flights to managing their finances. This is not a trend. This is a fundamental shift in how humans interact with services.

---

## ⚠️ The Challenge

> *"What if someone we don't know has built a new channel... and is speaking in our name?"*

Today, when a customer asks ChatGPT about energy prices or consumption advice, **we have no control over the response**. ChatGPT might recommend a competitor, give inaccurate information, or miss an opportunity to strengthen our relationship with the customer.

**The question is not IF this will happen. It's already happening.**

---

## 💡 Our Response

This POC demonstrates how Enovos can **anticipate and take advantage** of the AI revolution by directly integrating with ChatGPT through the MCP (Model Context Protocol).

Instead of letting AI speak about us, **we give AI the tools to speak FOR us**.

### What We Gain

| Benefit | How |
|---------|-----|
| 🎯 **Know our customers better** | AI analyzes consumption patterns, identifies profiles |
| 💚 **Fidelization** | Personalized advice, challenges, rewards |
| 📢 **Nudge behavior** | Guide customers toward better contracts, energy sharing |
| 🎮 **Control our marketing** | We define the offers, the messaging, the recommendations |
| 🧠 **Combine intelligences** | Our data + AI reasoning = superior customer experience |
| 🏆 **Be among the most innovative** | Present in the AI marketplace |
| 🌐 **Multilingual by default** | ChatGPT handles any language |
| 🎤 **Future-ready** | Voice, video - the interface evolves, our backend stays |

---

## 🎬 Demo Scenario

```
👩 Maria: "I heard energy prices were amazingly high lately..."

👨 Colleague: "Really? Let me ask ChatGPT."

👨 "Enovos, what was my consumption in 2023? I am customer 00042."

👨 "Hmm, okay. How does it compare to the previous year? Can you display it?"

👩 (worried) "This is much more..."

👨 "Wow, this is much more! Can you please help me and give specific advice?"

👨 "Can you provide more specific recommendations?"

🤖 ChatGPT: "Based on your profile, I recommend Energy Sharing..."

👩 "But I don't know anyone to share with..."

👨 "Can you find a partner please?"

🤖 ChatGPT: "I found 3 solar producers in your area. 
    Want me to register your interest?"
```

**Result**: Customer stays with Enovos, gets personalized advice, discovers new services, feels understood.

---

## 🏗️ Architecture

```
┌─────────────────┐       HTTPS/SSE        ┌───────────────────────────┐
│                 │◄──────────────────────►│      AWS EC2 Instance     │
│    ChatGPT      │        (ngrok)         │                           │
│                 │                        │   ┌───────────────────┐   │
│  "The new       │                        │   │    MCP Server     │   │
│   channel"      │                        │   │   (Our voice)     │   │
│                 │                        │   └─────────┬─────────┘   │
└─────────────────┘                        │             │             │
        │                                  │   ┌─────────▼─────────┐   │
        │                                  │   │   Customer Data   │   │
   Millions of                             │   │   (Load curves)   │   │
   users daily                             │   └───────────────────┘   │
        │                                  │                           │
        ▼                                  └───────────────────────────┘
   🗣️ Voice                                            │
   📹 Video                                            ▼ (Roadmap)
   🌐 Any language                            ┌───────────────┐
                                              │   DynamoDB    │
                                              │   Real CRM    │
                                              └───────────────┘
```

---

## 🛠️ MCP Tools (11 Services)

### 📊 Customer Data Access
| Tool | Purpose |
|------|---------|
| `get_consumption_hourly` | Detailed consumption analysis |
| `get_consumption_daily` | Day-by-day trends |
| `get_consumption_monthly` | Monthly overview |
| `get_annual_summary` | **Full year summary** with cost estimate & comparison |

### 🧠 Intelligence Layer
| Tool | Purpose |
|------|---------|
| `get_customer_profile` | AI classification: EV, heat pump, office, residential |
| `get_customer_contract` | Current contract info |
| `get_enovos_offers` | Our offers with smart matching |
| `get_advice` | Workflow to guide AI recommendations |

### 🎮 Engagement & Growth
| Tool | Purpose |
|------|---------|
| `get_challenges` | Gamification - energy saving with rewards |
| `find_sharing_partners` | Energy Sharing - connect producers & consumers |
| `signal_interest` | Capture leads, initiate partnerships |

---

## 🔮 Smart Profile Detection

The system automatically identifies customer types:

| Profile | Detection | We Recommend |
|---------|-----------|--------------|
| 🚗 **EV Owner** | Night charging pattern | Naturstrom Drive |
| 🔥 **Heat Pump** | High winter consumption | Naturstrom Fix |
| 🏢 **Office** | Daytime consumption | Energy Sharing |
| 🏠 **Residential** | Standard pattern | Nova Naturstroum |

**This is nudging in action** - we guide AI to recommend what's best for each customer AND for Enovos.

---

## ⚙️ Technical Setup

### Prerequisites
- AWS EC2 instance
- Python 3.11+
- ngrok (HTTPS tunnel)

### Quick Start

```bash
# On EC2
git clone https://github.com/czheadeth/enovosmcp.git
cd enovosmcp
python3.11 -m pip install -r requirements.txt
nohup python3.11 -m src.server > server.log 2>&1 &

# Start ngrok tunnel
./ngrok http 8000
```

### Connect to ChatGPT

1. Settings → Connectors → Add MCP
2. Paste ngrok URL: `https://xxx.ngrok-free.dev/mcp/sse`
3. Start the conversation!

---

## ⚠️ Important Note

**This is a POC.** Not everything is production-ready:
- Customer consent flows are assumed
- Data is anonymized/synthetic
- Security hardening needed for production

But the concept is proven. **This world is coming.**

---

## 🚀 What's Next?

- [ ] Real customer data integration (with consent)
- [ ] DynamoDB for scalability
- [ ] Integration with existing CRM
- [ ] Voice interface testing
- [ ] Multi-language validation
- [ ] Production security audit

---

## 🎯 Key Takeaways

1. **ChatGPT is the new channel** - We must be present
2. **Control the narrative** - If we don't, someone else will
3. **Nudge intelligently** - Guide AI to recommend OUR solutions
4. **Combine intelligences** - Our domain expertise + AI capabilities
5. **Future-proof** - Voice, video, whatever comes next

---

## 👥 Team

**Enovos Luxembourg** - Energy Hackathon 2024

*"Know our customers better. Be where they are."*

---

## 📄 License

MIT License

---

<p align="center">
  <b>⚡ The AI revolution is here. Let's lead it. ⚡</b>
</p>
