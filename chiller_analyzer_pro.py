import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import pdfkit
import os
from datetime import datetime
from dotenv import load_dotenv


# --- Page Setup ---
st.set_page_config(page_title="Smart Chiller Plant Analyzer", layout="wide")
st.title("🏭 Smart Chiller Plant Analyzer")

# --- Unit System ---
unit_system = st.sidebar.radio("Unit System", ["SI", "I-P"])

# --- Manual Equipment Inputs ---
st.header("🧊 Chiller Inputs")
num_chillers = st.slider("Number of Chillers", 1, 5, 2)
chiller_data = []
for i in range(num_chillers):
    st.subheader(f"Chiller {i+1}")
    name = st.text_input(f"Name", value=f"Chiller {i+1}", key=f"name_{i}")
    cap = st.number_input("Cooling Capacity (kW)", value=100.0, key=f"cap_{i}")
    power = st.number_input("Power Input (kW)", value=60.0, key=f"power_{i}")
    if unit_system == "I-P":
        eer = (cap * 12000) / (power * 1000)
        cop = eer / 3.412
        kw_per_ton = power / cap
    else:
        cop = cap / power
        eer = cop * 3.412
        kw_per_ton = 3.5 / cop
    chiller_data.append({
        "Name": name,
        "Capacity": cap,
        "Power": power,
        "COP": round(cop, 2),
        "EER": round(eer, 2),
        "kW/Ton": round(kw_per_ton, 2)
    })
    st.success(f"{name} → COP: {round(cop,2)}, EER: {round(eer,2)}, kW/Ton: {round(kw_per_ton,2)}")

# --- Pump Inputs ---
st.header("🚰 Pump Inputs")
pump_name = st.text_input("Pump Name", value="Main Pump")
flow = st.number_input("Flow Rate (m³/s)", value=0.02)
head = st.number_input("Head (m)", value=30.0)
pump_power = st.number_input("Pump Power Input (kW)", value=6.0)
density = 1000 if unit_system == "SI" else 62.4 * 1.3558
g = 9.81 if unit_system == "SI" else 32.174
hydraulic_power = flow * head * density * g / 1000
pump_eff = (hydraulic_power / pump_power) * 100
st.success(f"{pump_name} → Efficiency: {round(pump_eff, 2)}%")

# --- Cooling Tower Inputs ---
st.header("🌫️ Cooling Tower Inputs")
tower_name = st.text_input("Cooling Tower Name", value="CT Unit 1")
cw_in = st.number_input("CW Inlet Temp (°C)", value=35.0)
cw_out = st.number_input("CW Outlet Temp (°C)", value=30.0)
wet_bulb = st.number_input("Wet Bulb Temp (°C)", value=28.0)
CT_range = cw_in - cw_out
approach = cw_out - wet_bulb
effectiveness = CT_range / (CT_range + approach)
st.success(f"{tower_name} → CT_Range: {CT_range}°, Approach: {approach}°, Effectiveness: {round(effectiveness*100,2)}%")

# --- AI Recommendations ---
st.header("🧠 AI Recommendations")
for chiller in chiller_data:
    if chiller["COP"] < 3.5:
        st.warning(f"{chiller['Name']} may benefit from maintenance or load redistribution.")
    else:
        st.info(f"{chiller['Name']} is operating efficiently.")
if pump_eff < 60:
    st.warning(f"{pump_name} has low efficiency.")
if effectiveness < 0.5:
    st.warning(f"{tower_name} has low effectiveness.")

# --- Simulated Load Profile ---
st.header("📊 Simulated Load Profile")
base_load = st.slider("🔧 Base Cooling Load (kW)", 300, 1000, 600)
ambient_temp = st.slider("🌡️ Ambient Temp (°C)", 25, 45, 35)
profile = []
timestamps = []
for hour in range(24):
    time = datetime(2025, 7, 25, hour)
    timestamps.append(time.strftime("%H:%M"))
    load_factor = 0.6 + 0.4 * np.exp(-((hour - 14) ** 2) / 20)
    temp_factor = 1 + (ambient_temp - 30) * 0.02
    profile.append(round(base_load * load_factor * temp_factor, 2))

fig, ax = plt.subplots()
ax.plot(timestamps, profile, marker='o')
ax.set_title("Simulated Cooling Load Profile")
ax.set_xlabel("Time")
ax.set_ylabel("Cooling Load (kW)")
plt.xticks(rotation=45)
st.pyplot(fig)

# --- Chiller Sequencing ---
st.header("🔁 Chiller Sequencing Logic")
total_capacity = sum([chiller["Capacity"] for chiller in chiller_data])
st.info(f"🧊 Total Chiller Capacity: {total_capacity} kW")

for i, load in enumerate(profile):
    active_chillers = []
    remaining_load = load
    for chiller in chiller_data:
        if remaining_load <= 0:
            break
        cap = chiller["Capacity"]
        cop = chiller["COP"]
        if remaining_load >= cap:
            active_chillers.append((chiller["Name"], cap, cop))
            remaining_load -= cap
        else:
            active_chillers.append((chiller["Name"], remaining_load, cop))
            remaining_load = 0
    st.write(f"🕒 {timestamps[i]} → Load: {load} kW")
    for entry in active_chillers:
        st.write(f"• {entry[0]} → Load: {entry[1]} kW | COP: {round(entry[2],2)}")

# --- Interactive Chart ---
st.header("📈 Chiller COP vs Load")
fig2, ax2 = plt.subplots()
for chiller in chiller_data:
    loads = [25, 50, 75, 100]
    cop_vals = [chiller["COP"] * (1 - 0.1 * (1 - l / 100)) for l in loads]
    ax2.plot(loads, cop_vals, label=chiller["Name"])
ax2.set_title("Chiller COP vs Load")
ax2.set_xlabel("Load (%)")
ax2.set_ylabel("COP")
ax2.legend()
st.pyplot(fig2)

# --- PDF Export ---
st.header("📄 Export PDF Report")
if st.button("Generate PDF"):
    html = f"<h1>Chiller Report</h1><ul>"
    for chiller in chiller_data:
        html += f"<li>{chiller['Name']}: COP={chiller['COP']}, EER={chiller['EER']}, kW/Ton={chiller['kW/Ton']}</li>"
    html += f"<li>{pump_name}: Efficiency={round(pump_eff,2)}%</li>"
    html += f"<li>{tower_name}: Effectiveness={round(effectiveness*100,2)}%</li>"
    html += "</ul>"
    os.makedirs("templates", exist_ok=True)
    with open("templates/report_template.html", "w") as f:
        f.write(html)
    pdfkit.from_file("templates/report_template.html", "report.pdf")
    st.success("✅ PDF report generated!")

